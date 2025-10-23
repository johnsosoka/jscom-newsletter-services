################################
# Lambda Outputs
################################

output "newsletter_api_public_function_name" {
  description = "Name of the newsletter public API Lambda function"
  value       = module.newsletter-api-public.lambda_function_name
}

output "newsletter_sqs_processor_function_name" {
  description = "Name of the newsletter SQS processor Lambda function"
  value       = module.newsletter-sqs-processor.lambda_function_name
}

output "newsletter_api_admin_function_name" {
  description = "Name of the newsletter admin API Lambda function"
  value       = module.newsletter-api-admin.lambda_function_name
}

output "newsletter_admin_authorizer_function_name" {
  description = "Name of the newsletter admin authorizer Lambda function"
  value       = module.newsletter-admin-authorizer.lambda_function_name
}

################################
# API Gateway Outputs
################################

output "newsletter_api_endpoint" {
  description = "Base URL for newsletter API endpoints"
  value       = "https://${local.api_domain_name}/v1/newsletter"
}

output "newsletter_admin_api_endpoint" {
  description = "Base URL for newsletter admin API endpoints"
  value       = "https://${local.api_domain_name}/v1/newsletter/admin"
}

output "newsletter_public_routes" {
  description = "Available public newsletter API routes"
  value = {
    subscribe   = "POST /v1/newsletter"
    unsubscribe = "DELETE /v1/newsletter"
    status      = "GET /v1/newsletter/status"
  }
}

output "newsletter_admin_routes" {
  description = "Available admin newsletter API routes (requires x-api-key header)"
  value = {
    list_subscribers = "GET /v1/newsletter/admin/subscribers"
    get_subscriber   = "GET /v1/newsletter/admin/subscribers/{id}"
    update_status    = "PUT /v1/newsletter/admin/subscribers/{id}/status"
    delete_subscriber = "DELETE /v1/newsletter/admin/subscribers/{id}"
  }
}

################################
# DynamoDB Outputs
################################

output "newsletter_subscribers_table_name" {
  description = "Name of the newsletter subscribers DynamoDB table"
  value       = aws_dynamodb_table.newsletter_subscribers.name
}

################################
# SQS Outputs
################################

output "newsletter_operations_queue_url" {
  description = "URL of the newsletter operations SQS queue"
  value       = aws_sqs_queue.newsletter_operations_queue.id
}
