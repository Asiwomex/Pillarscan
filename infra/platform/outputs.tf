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

output "cognito_domain" {
  description = "Address of the Cognito sign-in pages."
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.region}.amazoncognito.com"
}

output "cognito_client_id" {
  description = "ID of the site's app client. Public: it identifies the site, it is not a secret."
  value       = aws_cognito_user_pool_client.site.id
}

output "user_pool_id" {
  description = "The pool to create users in."
  value       = aws_cognito_user_pool.this.id
}

output "role_template_url" {
  value = "https://${aws_s3_bucket.onboarding.bucket_regional_domain_name}/${aws_s3_object.role_template.key}"
}
