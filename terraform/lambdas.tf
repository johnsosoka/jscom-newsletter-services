################################
# Newsletter API Public
################################

module "newsletter-api-public" {
  source          = "terraform-aws-modules/lambda/aws"
  function_name   = var.newsletter_api_public_lambda_name
  description     = "Public API handler for newsletter subscription operations (subscribe, unsubscribe, status)"
  runtime         = "python3.13"                                      # AL2023
  handler         = "newsletter_api_public_lambda.lambda_handler"     # app/newsletter_api_public_lambda.py
  build_in_docker = true                                              # build deps for Linux

  source_path = [{
    path             = "${path.module}/../lambdas/src/newsletter-api-public/app"
    pip_requirements = "${path.module}/../lambdas/src/newsletter-api-public/requirements.txt"
  }]

  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.newsletter_operations_queue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query"]
        Resource = [
          aws_dynamodb_table.newsletter_subscribers.arn,
          "${aws_dynamodb_table.newsletter_subscribers.arn}/index/email-index"
        ]
      }
    ]
  })

  environment_variables = {
    NEWSLETTER_OPERATIONS_QUEUE_URL  = aws_sqs_queue.newsletter_operations_queue.id
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME = aws_dynamodb_table.newsletter_subscribers.name
  }

  tags = {
    project = local.project_name
  }
}

################################
# Newsletter SQS Processor
################################

module "newsletter-sqs-processor" {
  source          = "terraform-aws-modules/lambda/aws"
  function_name   = var.newsletter_sqs_processor_lambda_name
  description     = "SQS processor that handles newsletter operations from the queue"
  runtime         = "python3.13"
  handler         = "newsletter_sqs_processor_lambda.lambda_handler" # app/newsletter_sqs_processor_lambda.py
  build_in_docker = true

  source_path = [{
    path             = "${path.module}/../lambdas/src/newsletter-sqs-processor/app"
    pip_requirements = "${path.module}/../lambdas/src/newsletter-sqs-processor/requirements.txt"
  }]

  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.newsletter_operations_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.newsletter_subscribers.arn,
          "${aws_dynamodb_table.newsletter_subscribers.arn}/index/email-index"
        ]
      }
    ]
  })

  environment_variables = {
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME = aws_dynamodb_table.newsletter_subscribers.name
  }

  tags = {
    project = local.project_name
  }
}

resource "aws_lambda_event_source_mapping" "newsletter_sqs_processor_mapping" {
  event_source_arn = aws_sqs_queue.newsletter_operations_queue.arn
  function_name    = module.newsletter-sqs-processor.lambda_function_arn
}

################################
# Newsletter API Admin
################################

module "newsletter-api-admin" {
  source          = "terraform-aws-modules/lambda/aws"
  function_name   = var.newsletter_api_admin_lambda_name
  description     = "Admin API handler for managing newsletter subscribers"
  runtime         = "python3.13"
  handler         = "newsletter_api_admin_lambda.lambda_handler" # app/newsletter_api_admin_lambda.py
  architectures   = ["x86_64"]
  build_in_docker = true

  # Force x86_64 build on ARM64 host (Apple Silicon Mac)
  docker_additional_options = ["--platform", "linux/amd64"]

  source_path = [{
    path             = "${path.module}/../lambdas/src/newsletter-api-admin/app"
    pip_requirements = "${path.module}/../lambdas/src/newsletter-api-admin/requirements.txt"
  }]

  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.newsletter_subscribers.arn,
          "${aws_dynamodb_table.newsletter_subscribers.arn}/index/email-index",
          "${aws_dynamodb_table.newsletter_subscribers.arn}/index/status-index"
        ]
      }
    ]
  })

  environment_variables = {
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME = aws_dynamodb_table.newsletter_subscribers.name
  }

  tags = {
    project = local.project_name
  }
}

################################
# Newsletter Admin Authorizer
################################

module "newsletter-admin-authorizer" {
  source          = "terraform-aws-modules/lambda/aws"
  function_name   = var.newsletter_admin_authorizer_lambda_name
  description     = "Lambda authorizer for newsletter admin API key validation"
  runtime         = "python3.13"
  handler         = "newsletter_admin_authorizer_lambda.lambda_handler" # app/newsletter_admin_authorizer_lambda.py
  build_in_docker = false

  source_path = [{
    path             = "${path.module}/../lambdas/src/newsletter-admin-authorizer/app"
    pip_requirements = false
  }]

  environment_variables = {
    ADMIN_API_KEY = var.admin_api_key_value
  }

  tags = {
    project = local.project_name
  }
}
