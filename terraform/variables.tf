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

variable "newsletter_admin_authorizer_lambda_name" {
  description = "Name for the newsletter admin authorizer Lambda function"
  type        = string
  default     = "newsletter-admin-authorizer"
}

# Admin API Key Configuration
variable "admin_api_key_value" {
  description = "API key value for admin endpoints (store securely, generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
}
