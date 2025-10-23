resource "aws_sqs_queue" "newsletter_operations_queue" {
  name                      = "newsletter-operations-queue"
  visibility_timeout_seconds = 30
  message_retention_seconds = 345600 # 4 days

  tags = {
    project = local.project_name
  }
}
