variable "newsletter_api_public_lambda_name" {
  description = "Name for the public newsletter API Lambda function"
  type        = string
  default     = "newsletter-api-public"
}

variable "newsletter_sqs_processor_lambda_name" {
  description = "Name for the newsletter SQS processor Lambda function"
  type        = string
  default     = "newsletter-sqs-processor"
}

variable "newsletter_api_admin_lambda_name" {
  description = "Name for the admin newsletter API Lambda function"
  type        = string
  default     = "newsletter-api-admin"
}

# Admin authorization is now handled by Cognito JWT tokens
# No API key or Lambda authorizer needed
