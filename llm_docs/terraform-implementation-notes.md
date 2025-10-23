# Terraform Implementation Notes

## Date: 2025-10-22

## Overview

Created complete Terraform configuration for jscom-newsletter-services project following the established patterns from jscom-contact-services. The infrastructure provisions a serverless newsletter management system with 4 Lambda functions, DynamoDB table with GSIs, SQS queue, and API Gateway v2 integrations.

## Files Created

1. **main.tf** - Provider configuration, S3 backend, and remote state references
2. **variables.tf** - Variable definitions for Lambda names and admin API key
3. **dynamoDB.tf** - DynamoDB table with two Global Secondary Indexes
4. **sqs.tf** - SQS queue for newsletter operations
5. **lambdas.tf** - All 4 Lambda function modules and event source mapping
6. **api-gateway.tf** - API Gateway integrations, routes, and authorizer
7. **outputs.tf** - Useful output values for all resources
8. **terraform.tfvars.example** - Template for required variables

## Architecture Decisions

### Lambda Functions

All Lambda functions use the `terraform-aws-modules/lambda/aws` module with consistent patterns:

1. **newsletter-api-public**
   - Handles public API endpoints (POST/DELETE/GET /v1/newsletter)
   - Has permissions for SQS SendMessage and DynamoDB Query (email-index)
   - Uses `build_in_docker = true` for Python dependencies

2. **newsletter-sqs-processor**
   - Triggered by SQS queue via event source mapping
   - Has permissions for SQS and DynamoDB operations
   - Processes subscription operations asynchronously

3. **newsletter-api-admin**
   - Handles admin API endpoint (ANY /v1/newsletter/admin/{proxy+})
   - Full DynamoDB permissions (read/write on table and both GSIs)
   - Uses catch-all route with {proxy+} pattern for flexible routing
   - Requires Apple Silicon compatibility flags:
     - `architectures = ["x86_64"]`
     - `docker_additional_options = ["--platform", "linux/amd64"]`

4. **newsletter-admin-authorizer**
   - REQUEST authorizer for API Gateway v2
   - Validates x-api-key header
   - Uses `build_in_docker = false` (no dependencies)
   - Uses `enable_simple_responses = true` for boolean responses

### DynamoDB Table Design

**Table: newsletter-subscribers**
- Partition key: `id` (String)
- Billing mode: PAY_PER_REQUEST
- Two Global Secondary Indexes:
  - **email-index**: Hash key = `email`, Projection = ALL
  - **status-index**: Hash key = `status`, Projection = ALL

The GSIs enable efficient querying:
- email-index: Check if email already exists during subscription
- status-index: Admin operations to list subscribers by status

### API Gateway Integration

The project integrates with the existing API Gateway from jscom-blog project:
- Uses remote state to get `api_gateway_id` and `execution_arn`
- Creates 4 public routes (no authorization):
  - POST /v1/newsletter (subscribe)
  - DELETE /v1/newsletter (unsubscribe)
  - GET /v1/newsletter/status (check status)
- Creates 1 admin route (with authorizer):
  - ANY /v1/newsletter/admin/{proxy+} (admin operations)

### Lambda Authorizer Configuration

The API Gateway v2 authorizer is configured as:
- Type: REQUEST (not TOKEN)
- Payload format version: 2.0
- Simple responses: enabled (returns boolean instead of policy document)
- Identity source: `$request.header.x-api-key`

This matches the jscom-contact-services pattern and works with the Lambda authorizer's simple boolean response format.

### SQS Queue Configuration

**Queue: newsletter-operations-queue**
- Visibility timeout: 30 seconds (default)
- Message retention: 4 days (345600 seconds)
- Event source mapping connects queue to newsletter-sqs-processor Lambda

The 4-day retention ensures operations aren't lost if processing fails temporarily.

## IAM Permissions

All IAM policies follow least-privilege principles:

**newsletter-api-public:**
- SQS: SendMessage on operations queue only
- DynamoDB: Query on table and email-index GSI only (read-only, specific operations)

**newsletter-sqs-processor:**
- SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes on operations queue
- DynamoDB: GetItem, PutItem, UpdateItem, Query on table and email-index GSI

**newsletter-api-admin:**
- DynamoDB: Full CRUD operations (GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan)
- Permissions granted on table and both GSIs

**newsletter-admin-authorizer:**
- No AWS permissions needed (only reads environment variable)

## Remote State Dependencies

The configuration depends on two remote Terraform states:

1. **jscom-core-infra** (`jscom_common_data`)
   - Not actively used but follows established pattern
   - Provides shared infrastructure references

2. **jscom-blog** (`jscom_web_data`)
   - Provides API Gateway instance that this project integrates with
   - Required outputs:
     - `api_gateway_id` - Gateway to add routes to
     - `api_gateway_execution_arn` - For Lambda permissions
     - `custom_domain_name` - api.johnsosoka.com
     - `custom_domain_name_target` - For DNS configuration

## Source Path Configuration

Lambda source paths follow the established pattern:
- Path points to `app/` directory within each Lambda
- `pip_requirements` points to `requirements.txt` in Lambda root
- Exception: newsletter-admin-authorizer has `pip_requirements = false` (no dependencies)

**Example structure:**
```
lambdas/src/newsletter-api-public/
  app/
    newsletter_api_public_lambda.py
  requirements.txt
  test/
```

## Configuration Management

**Sensitive Variables:**
- `admin_api_key_value` is marked as sensitive
- Must be provided in `terraform.tfvars` (not in version control)
- Example template provided in `terraform.tfvars.example`

**Generation command:**
```bash
openssl rand -hex 32
```

## Testing Considerations

Before applying:
1. Ensure AWS_PROFILE=jscom is set
2. Verify remote state buckets are accessible
3. Confirm jscom-blog API Gateway exists
4. Run `terraform init` to download modules
5. Run `terraform plan` to verify configuration
6. Review plan output for expected resources

## Known Patterns from Contact Services

The implementation closely mirrors jscom-contact-services with these key patterns:

1. **Lambda Module Usage:**
   - Consistent use of `terraform-aws-modules/lambda/aws`
   - Docker builds for functions with dependencies
   - Proper handler format: `<filename>.lambda_handler`

2. **API Gateway v2 Format:**
   - Payload format version 2.0
   - AWS_PROXY integration type
   - POST integration method for Lambda
   - Proper source_arn wildcards for Lambda permissions

3. **Event Source Mapping:**
   - Direct mapping from SQS to Lambda
   - No additional configuration needed
   - Lambda automatically handles batch processing

4. **Resource Naming:**
   - Consistent kebab-case for resource names
   - Project tag on all resources
   - Clear, descriptive resource names

## Next Steps

1. Create `terraform.tfvars` with actual admin API key
2. Run `terraform init` with AWS_PROFILE=jscom
3. Run `terraform plan` to review changes
4. Run `terraform apply` to create infrastructure
5. Test public API endpoints (no auth required)
6. Test admin API endpoints (with x-api-key header)
7. Monitor CloudWatch logs for all Lambda functions
8. Verify SQS queue processing and DynamoDB writes

## Important Notes

- Lambda functions use Python 3.13 runtime (Amazon Linux 2023)
- All functions built in Docker for Linux compatibility
- Admin Lambda requires x86_64 architecture flags for Apple Silicon
- API Gateway already exists (from jscom-blog project)
- Only adds routes/integrations to existing gateway
- DynamoDB table uses PAY_PER_REQUEST billing (no capacity management needed)
- SQS visibility timeout matches default (30 seconds)
- Message retention set to 4 days for reliability
