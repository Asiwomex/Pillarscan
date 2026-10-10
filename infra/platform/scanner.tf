# Scan requests go through a queue so that asking for a scan returns at
# once and a failed scan is retried, then set aside, instead of lost.

resource "aws_sqs_queue" "scan_dead_letter" {
  name                      = "pillarscan-scan-dead-letter"
  message_retention_seconds = 14 * 24 * 60 * 60
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "scan_requests" {
  name                    = "pillarscan-scan-requests"
  sqs_managed_sse_enabled = true

  # Must be longer than the function can run, or a message could be handed
  # to a second invocation while the first is still scanning. AWS suggests
  # six times the function timeout.
  visibility_timeout_seconds = 6 * aws_lambda_function.scanner.timeout

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scan_dead_letter.arn
    maxReceiveCount     = 2
  })
}

data "archive_file" "scanner" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/scanner"
  output_path = "${path.module}/.build/scanner.zip"
}

resource "aws_cloudwatch_log_group" "scanner" {
  name              = "/aws/lambda/pillarscan-scanner"
  retention_in_days = local.log_retention_days
}

resource "aws_lambda_function" "scanner" {
  function_name = "pillarscan-scanner"
  description   = "Assumes the read-only audit role, runs every check and stores the scan."

  role          = aws_iam_role.scanner.arn
  runtime       = local.lambda_runtime
  architectures = [local.lambda_architecture]
  handler       = "scanner.lambda_handler.handler"

  filename         = data.archive_file.scanner.output_path
  source_code_hash = data.archive_file.scanner.output_base64sha256

  # A scan is mostly waiting on AWS APIs across many threads. More memory
  # also means more CPU, which shortens it. Typical run: under a minute.
  timeout     = 120
  memory_size = 1024

  environment {
    variables = {
      TABLE_NAME            = aws_dynamodb_table.scans.name
      AUDIT_ROLE_ARN        = local.audit_role_arn
      EXTERNAL_ID_PARAMETER = var.external_id_parameter
    }
  }

  depends_on = [aws_cloudwatch_log_group.scanner]
}

resource "aws_lambda_event_source_mapping" "scan_requests" {
  event_source_arn = aws_sqs_queue.scan_requests.arn
  function_name    = aws_lambda_function.scanner.arn
  batch_size       = 1

  # Never more than two scans at once, whatever arrives on the queue.
  scaling_config {
    maximum_concurrency = 2
  }
}

# The function's own role. It cannot read the account's resources itself:
# all it may do is log, take messages, write scans, read one parameter and
# assume the audit role.
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scanner" {
  name               = "pillarscan-scanner"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "scanner" {
  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.scanner.arn}:*"]
  }

  statement {
    sid       = "TakeScanRequests"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.scan_requests.arn]
  }

  statement {
    sid = "StoreScansAndReadConnectedAccounts"
    actions = [
      "dynamodb:BatchWriteItem",
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.scans.arn]
  }

  statement {
    sid       = "ReadExternalId"
    actions   = ["ssm:GetParameter"]
    resources = [local.external_id_parameter_arn]
  }

  # Audit roles in any account, but only ones with this name. Each of those
  # roles decides for itself whether to let this function in, by checking
  # the caller and the external ID.
  statement {
    sid       = "AssumeAuditRoles"
    actions   = ["sts:AssumeRole"]
    resources = ["arn:aws:iam::*:role/${var.audit_role_name}*"]
  }
}

resource "aws_iam_role_policy" "scanner" {
  name   = "scanner"
  role   = aws_iam_role.scanner.id
  policy = data.aws_iam_policy_document.scanner.json
}

# A daily scan, so the dashboard has a history to show. The schedule only
# drops a message on the queue; the same path a "run scan" button will use.
resource "aws_scheduler_schedule" "daily_scan" {
  name                = "pillarscan-daily-scan"
  schedule_expression = var.scan_schedule

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sqs_queue.scan_requests.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ source = "schedule" })
  }
}

data "aws_iam_policy_document" "scheduler_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    # Only schedules in this account may use the role.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "pillarscan-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_trust.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RequestScan"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scan_requests.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "request-scan"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}
