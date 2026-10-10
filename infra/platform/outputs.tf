output "api_url" {
  description = "Base URL of the API. The site reads it from NEXT_PUBLIC_API_URL."
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "scan_queue_url" {
  description = "Send a message here to request a scan."
  value       = aws_sqs_queue.scan_requests.url
}

output "table_name" {
  value = aws_dynamodb_table.scans.name
}
