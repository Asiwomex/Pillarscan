# Two alarms cover the ways a scan can go wrong: the function raised an
# error, or a request failed twice and landed in the dead-letter queue.
# CloudWatch's always-free allowance includes ten alarms.

resource "aws_sns_topic" "alarms" {
  count = var.alarm_email == "" ? 0 : 1
  name  = "pillarscan-alarms"
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

locals {
  alarm_actions = aws_sns_topic.alarms[*].arn
}

resource "aws_cloudwatch_metric_alarm" "scanner_errors" {
  alarm_name        = "pillarscan-scanner-errors"
  alarm_description = "The scanner Lambda raised an error. Check its log group."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = aws_lambda_function.scanner.function_name
  }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  # No data means the function did not run, which is the normal state.
  treat_missing_data = "notBreaching"

  alarm_actions = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "dead_letters" {
  alarm_name        = "pillarscan-scan-dead-letters"
  alarm_description = "A scan request failed twice and is waiting in the dead-letter queue."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  dimensions = {
    QueueName = aws_sqs_queue.scan_dead_letter.name
  }

  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = local.alarm_actions
}
