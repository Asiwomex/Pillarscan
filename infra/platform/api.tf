data "archive_file" "api" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/api"
  output_path = "${path.module}/.build/api.zip"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/pillarscan-api"
  retention_in_days = local.log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name = "pillarscan-api"
  description   = "HTTP API over stored scans and connected accounts (FastAPI)."

  role          = aws_iam_role.api.arn
  runtime       = local.lambda_runtime
  architectures = [local.lambda_architecture]
  handler       = "api.handler.handler"

  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256

  timeout     = 10
  memory_size = 256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.scans.name
      # Stored scans are scrubbed, so this placeholder is the only account
      # the API has anything for.
      PILLARSCAN_ACCOUNT_ID = "000000000000"
      SCAN_QUEUE_URL        = aws_sqs_queue.scan_requests.url
      SCANNER_ROLE_ARN      = aws_iam_role.scanner.arn
      ROLE_TEMPLATE_URL     = "https://${aws_s3_bucket.onboarding.bucket_regional_domain_name}/${aws_s3_object.role_template.key}"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api]
}

# The API can read scans, keep the list of connected accounts and put a
# scan request on the queue. It cannot assume any role, so it can never
# look inside an AWS account itself.
resource "aws_iam_role" "api" {
  name               = "pillarscan-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "api" {
  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }

  statement {
    sid = "ReadScansAndManageConnectedAccounts"
    actions = [
      "dynamodb:Query",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      # For disconnecting an account, which deletes the user's own scans.
      "dynamodb:DeleteItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [aws_dynamodb_table.scans.arn]
  }

  statement {
    sid       = "RequestScans"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scan_requests.arn]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "api"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

# An HTTP API is the cheaper, simpler kind of API Gateway, and all this
# needs: it forwards requests to one Lambda.
resource "aws_apigatewayv2_api" "this" {
  name          = "pillarscan"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.allowed_origins
    allow_methods = ["GET", "POST", "DELETE"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# Only the routes the API serves are exposed. Anything else gets a 404
# from API Gateway without invoking the function.
resource "aws_apigatewayv2_route" "api" {
  for_each = toset(["GET /health", "GET /scans", "GET /scans/{scan_id}"])

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

# Routes for signed-in users. API Gateway checks the Cognito token itself
# and turns away anything without a valid one before the function runs.
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    issuer   = "https://${aws_cognito_user_pool.this.endpoint}"
    audience = [aws_cognito_user_pool_client.site.id]
  }
}

resource "aws_apigatewayv2_route" "signed_in" {
  for_each = toset([
    "GET /me/accounts",
    "POST /me/accounts",
    "DELETE /me/accounts/{aws_account_id}",
    "POST /me/accounts/{aws_account_id}/scans",
    "GET /me/accounts/{aws_account_id}/scans",
    "GET /me/accounts/{aws_account_id}/scans/{scan_id}",
  ])

  api_id             = aws_apigatewayv2_api.this.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/pillarscan"
  retention_in_days = local.log_retention_days
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  # The API is public, so a low ceiling caps what abuse could cost: at most
  # 5 requests a second, with short bursts of 10.
  default_route_settings {
    throttling_rate_limit  = 5
    throttling_burst_limit = 10
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId = "$context.requestId"
      time      = "$context.requestTime"
      route     = "$context.routeKey"
      status    = "$context.status"
      latency   = "$context.responseLatency"
      sourceIp  = "$context.identity.sourceIp"
    })
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
