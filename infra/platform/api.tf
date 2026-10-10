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
  description   = "Read-only HTTP API over stored scans (FastAPI)."

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
    }
  }

  depends_on = [aws_cloudwatch_log_group.api]
}

# The API can read scans and write its own logs. It cannot write to the
# table, start a scan or assume any role.
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
    sid       = "ReadScans"
    actions   = ["dynamodb:Query", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.scans.arn]
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
    allow_methods = ["GET"]
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
