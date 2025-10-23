################################
# Public Newsletter API Integration
################################

resource "aws_apigatewayv2_integration" "newsletter_public_integration" {
  api_id                 = local.api_gateway_id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = module.newsletter-api-public.lambda_function_invoke_arn
  payload_format_version = "2.0"
}

# Public API Routes (no authorization required)
resource "aws_apigatewayv2_route" "newsletter_subscribe" {
  api_id    = local.api_gateway_id
  route_key = "POST /v1/newsletter"
  target    = "integrations/${aws_apigatewayv2_integration.newsletter_public_integration.id}"
}

resource "aws_apigatewayv2_route" "newsletter_unsubscribe" {
  api_id    = local.api_gateway_id
  route_key = "DELETE /v1/newsletter"
  target    = "integrations/${aws_apigatewayv2_integration.newsletter_public_integration.id}"
}

resource "aws_apigatewayv2_route" "newsletter_status" {
  api_id    = local.api_gateway_id
  route_key = "GET /v1/newsletter/status"
  target    = "integrations/${aws_apigatewayv2_integration.newsletter_public_integration.id}"
}

# Lambda permission for public API
resource "aws_lambda_permission" "newsletter_public_lambda_permission" {
  statement_id  = "AllowNewsletterPublicAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.newsletter-api-public.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.execution_arn}/*/*/*"
}

################################
# Admin Lambda Authorizer
################################

# Authorizer is now provided by the shared lambda-authorizer module
# in lambdas.tf - no additional resources needed here

################################
# Admin Newsletter API Integration
################################

resource "aws_apigatewayv2_integration" "newsletter_admin_integration" {
  api_id                 = local.api_gateway_id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = module.newsletter-api-admin.lambda_function_invoke_arn
  payload_format_version = "2.0"
}

# Catch-all route for admin endpoints: ANY /v1/newsletter/admin/{proxy+}
resource "aws_apigatewayv2_route" "newsletter_admin_route" {
  api_id    = local.api_gateway_id
  route_key = "ANY /v1/newsletter/admin/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.newsletter_admin_integration.id}"

  authorization_type = "CUSTOM"
  authorizer_id      = module.newsletter-admin-authorizer.authorizer_id
}

# Lambda permission for API Gateway to invoke admin Lambda
resource "aws_lambda_permission" "newsletter_admin_lambda_permission" {
  statement_id  = "AllowNewsletterAdminAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.newsletter-api-admin.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.execution_arn}/*/*/*"
}
