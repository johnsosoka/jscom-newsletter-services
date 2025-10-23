# Newsletter Services Terraform Configuration

This directory contains the complete Terraform configuration for the jscom-newsletter-services project, implementing a serverless newsletter management system on AWS.

## Architecture Overview

The infrastructure provisions:
- 4 Lambda functions (Python 3.13)
- 1 DynamoDB table with 2 Global Secondary Indexes
- 1 SQS queue for asynchronous processing
- API Gateway v2 integrations (reuses existing gateway from jscom-blog)
- Lambda authorizer for admin endpoints

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `main.tf` | 40 | Provider, S3 backend, remote state references |
| `variables.tf` | 30 | Variable definitions |
| `dynamoDB.tf` | 39 | DynamoDB table with GSIs |
| `sqs.tf` | 9 | SQS queue configuration |
| `lambdas.tf` | 181 | All 4 Lambda functions and event source mapping |
| `api-gateway.tf` | 96 | API Gateway integrations, routes, and authorizer |
| `outputs.tf` | 74 | Output values for all resources |
| `terraform.tfvars.example` | 3 | Template for required variables |

**Total:** 472 lines of Terraform configuration

## Prerequisites

1. AWS CLI configured with `jscom` profile
2. Terraform >= 1.0
3. Access to jscom-tf-backend S3 bucket
4. Existing API Gateway from jscom-blog project
5. Admin API key (generate with: `openssl rand -hex 32`)

## Setup

### 1. Create terraform.tfvars

Copy the example file and add your admin API key:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:
```hcl
admin_api_key_value = "your-generated-api-key-here"
```

Generate a secure key:
```bash
openssl rand -hex 32
```

**IMPORTANT:** Never commit `terraform.tfvars` to version control!

### 2. Initialize Terraform

```bash
export AWS_PROFILE=jscom
terraform init
```

This will:
- Download the AWS provider
- Download the Lambda module from Terraform Registry
- Configure the S3 backend
- Load remote state from jscom-core-infra and jscom-blog

### 3. Review the Plan

```bash
terraform plan
```

Expected resources to be created:
- 1 DynamoDB table
- 1 SQS queue
- 4 Lambda functions
- 1 Lambda event source mapping
- 2 API Gateway integrations
- 4 API Gateway routes
- 1 API Gateway authorizer
- 3 Lambda permissions

### 4. Apply Configuration

```bash
terraform apply
```

Review the plan and type `yes` to confirm.

## Lambda Functions

### 1. newsletter-api-public
**Handler:** `newsletter_api_public_lambda.lambda_handler`

Handles public API endpoints:
- `POST /v1/newsletter` - Subscribe to newsletter
- `DELETE /v1/newsletter` - Unsubscribe from newsletter
- `GET /v1/newsletter/status` - Check subscription status

**Permissions:**
- SQS: SendMessage to newsletter-operations-queue
- DynamoDB: Query on newsletter-subscribers table (email-index)

### 2. newsletter-sqs-processor
**Handler:** `newsletter_sqs_processor_lambda.lambda_handler`

Processes subscription operations from SQS queue asynchronously.

**Trigger:** SQS event source mapping

**Permissions:**
- SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes
- DynamoDB: GetItem, PutItem, UpdateItem, Query

### 3. newsletter-api-admin
**Handler:** `newsletter_api_admin_lambda.lambda_handler`

Handles admin API endpoints:
- `ANY /v1/newsletter/admin/{proxy+}` - All admin operations

**Authorization:** Requires `x-api-key` header

**Permissions:**
- DynamoDB: Full CRUD operations on newsletter-subscribers table

### 4. newsletter-admin-authorizer
**Handler:** `newsletter_admin_authorizer_lambda.lambda_handler`

API Gateway v2 REQUEST authorizer that validates the `x-api-key` header.

**Note:** No AWS permissions needed (reads environment variable only)

## DynamoDB Table

**Table Name:** `newsletter-subscribers`

**Primary Key:** `id` (String)

**Global Secondary Indexes:**
1. **email-index** - Hash key: `email`, Projection: ALL
2. **status-index** - Hash key: `status`, Projection: ALL

**Billing Mode:** PAY_PER_REQUEST (on-demand)

## SQS Queue

**Queue Name:** `newsletter-operations-queue`

**Configuration:**
- Visibility timeout: 30 seconds
- Message retention: 4 days (345600 seconds)

## API Endpoints

### Public Endpoints (No Authentication)

**Base URL:** `https://api.johnsosoka.com`

```bash
# Subscribe
POST /v1/newsletter
Content-Type: application/json

{
  "email": "user@example.com"
}

# Unsubscribe
DELETE /v1/newsletter
Content-Type: application/json

{
  "email": "user@example.com"
}

# Check Status
GET /v1/newsletter/status?email=user@example.com
```

### Admin Endpoints (Requires Authentication)

**Base URL:** `https://api.johnsosoka.com`

**Authentication:** Include `x-api-key` header with your admin API key

```bash
# List all subscribers
GET /v1/newsletter/admin/subscribers
x-api-key: your-admin-api-key

# Get specific subscriber
GET /v1/newsletter/admin/subscribers/{id}
x-api-key: your-admin-api-key

# Update subscriber status
PUT /v1/newsletter/admin/subscribers/{id}/status
x-api-key: your-admin-api-key
Content-Type: application/json

{
  "status": "active"
}

# Delete subscriber
DELETE /v1/newsletter/admin/subscribers/{id}
x-api-key: your-admin-api-key
```

## Remote State Dependencies

This configuration depends on remote state from:

### jscom-core-infra
```hcl
data.terraform_remote_state.jscom_common_data
```
Provides shared infrastructure references (not actively used but follows pattern)

### jscom-blog
```hcl
data.terraform_remote_state.jscom_web_data
```
Provides:
- `api_gateway_id` - API Gateway to integrate with
- `api_gateway_execution_arn` - For Lambda permissions
- `custom_domain_name` - api.johnsosoka.com
- `custom_domain_name_target` - For DNS configuration

## Outputs

After applying, Terraform will output:

```
newsletter_api_public_function_name
newsletter_sqs_processor_function_name
newsletter_api_admin_function_name
newsletter_admin_authorizer_function_name
newsletter_api_endpoint
newsletter_admin_api_endpoint
newsletter_public_routes
newsletter_admin_routes
newsletter_subscribers_table_name
newsletter_operations_queue_url
```

View outputs:
```bash
terraform output
```

## Troubleshooting

### Lambda Build Issues

If Lambda builds fail:
1. Ensure Docker is running (required for `build_in_docker = true`)
2. Check Lambda source paths are correct
3. Verify `requirements.txt` files exist

### API Gateway Integration Issues

If API Gateway routes don't work:
1. Verify jscom-blog remote state is accessible
2. Check API Gateway exists and is deployed
3. Verify Lambda permissions are correct

### DynamoDB Issues

If DynamoDB operations fail:
1. Verify table was created successfully
2. Check GSIs are active (can take a few minutes after creation)
3. Verify IAM permissions in Lambda policies

### Authorizer Issues

If admin endpoints return 401 Unauthorized:
1. Verify `x-api-key` header is included in requests
2. Check admin API key matches value in terraform.tfvars
3. Review authorizer Lambda logs in CloudWatch

## Maintenance

### Updating Lambda Code

After modifying Lambda source code:
```bash
terraform apply
```

Terraform will detect changes and rebuild/redeploy affected functions.

### Rotating Admin API Key

1. Generate new key: `openssl rand -hex 32`
2. Update `terraform.tfvars` with new key
3. Apply changes: `terraform apply`
4. Update clients with new key

### Viewing Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/newsletter-api-public --follow --profile jscom
aws logs tail /aws/lambda/newsletter-sqs-processor --follow --profile jscom
aws logs tail /aws/lambda/newsletter-api-admin --follow --profile jscom
aws logs tail /aws/lambda/newsletter-admin-authorizer --follow --profile jscom

# View SQS queue metrics
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw newsletter_operations_queue_url) \
  --attribute-names All \
  --profile jscom
```

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

**WARNING:** This will permanently delete:
- DynamoDB table and all subscriber data
- SQS queue and any pending messages
- All Lambda functions
- API Gateway routes (but not the gateway itself)

## Security Notes

1. **Admin API Key:**
   - Store securely (1Password, AWS Secrets Manager, etc.)
   - Never commit to version control
   - Rotate regularly
   - Use unique key per environment

2. **IAM Permissions:**
   - All Lambda policies follow least-privilege principle
   - Permissions limited to specific resources
   - No wildcard (*) permissions used

3. **API Gateway:**
   - Public endpoints are unauthenticated (by design)
   - Admin endpoints require valid x-api-key header
   - REQUEST authorizer validates keys server-side

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Global Secondary Indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
- [API Gateway v2 Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-lambda-authorizer.html)
- [Terraform AWS Lambda Module](https://registry.terraform.io/modules/terraform-aws-modules/lambda/aws/latest)

## Support

For issues or questions:
1. Check CloudWatch logs for Lambda functions
2. Review Terraform plan output for unexpected changes
3. Verify remote state dependencies are accessible
4. Consult implementation notes: `/llm_docs/terraform-implementation-notes.md`
