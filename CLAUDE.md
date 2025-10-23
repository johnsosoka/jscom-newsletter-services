# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Serverless newsletter management API system built on AWS Lambda, API Gateway, SQS, and DynamoDB. The system processes newsletter subscriptions through a hybrid architecture with synchronous reads and asynchronous writes.

## Architecture

Hybrid serverless architecture with four Lambda functions:

1. **API Gateway** → `newsletter-api-public` Lambda
   - POST `/v1/newsletter` - Subscribe to newsletter
   - DELETE `/v1/newsletter` - Unsubscribe from newsletter
   - GET `/v1/newsletter/status?email=...` - Check subscription status
   - Async operations (POST/DELETE) forward to SQS
   - Status checks query DynamoDB directly via email-index GSI

2. **newsletter-operations-queue** → `newsletter-sqs-processor` Lambda
   - Processes subscription operations from SQS
   - Checks for duplicate subscriptions via email-index GSI
   - Writes to `newsletter-subscribers` DynamoDB table
   - Sets status (active/inactive) with timestamps

3. **Admin API** → `newsletter-api-admin` Lambda (protected by authorizer)
   - GET `/v1/newsletter/admin/subscribers` - List subscribers with pagination
   - GET `/v1/newsletter/admin/subscribers/{id}` - Get single subscriber
   - GET `/v1/newsletter/admin/stats` - Get statistics
   - DELETE `/v1/newsletter/admin/subscribers/{id}` - Remove subscriber
   - PATCH `/v1/newsletter/admin/subscribers/{id}` - Update email address

## Project Structure

```
lambdas/
  src/
    newsletter-api-public/
      app/newsletter_api_public_lambda.py
      requirements.txt
      .venv/                   # Virtual environment for local development
    newsletter-sqs-processor/
      app/newsletter_sqs_processor_lambda.py
      requirements.txt
      .venv/
    newsletter-api-admin/
      app/newsletter_api_admin_lambda.py
      app/models.py            # Pydantic models
      app/handlers.py          # Business logic
      requirements.txt
      .venv/
    newsletter-admin-authorizer/
      app/newsletter_admin_authorizer_lambda.py
      requirements.txt
      .venv/

  test/                        # Integration tests (if needed)

terraform/
  main.tf                      # Provider, backend, remote state references
  lambdas.tf                   # Lambda function modules and event source mappings
  api-gateway.tf               # API Gateway v2 integration and routes
  dynamoDB.tf                  # DynamoDB table with GSIs
  sqs.tf                       # SQS queue
  variables.tf                 # Terraform variables
  terraform.tfvars             # Sensitive configuration (not in version control)

llm_docs/                      # Documentation from subagents
```

### Python Development Environment

Each Lambda function has its own isolated virtual environment for local development and testing.

**Virtual Environment Locations:**
- `lambdas/src/newsletter-api-public/.venv/`
- `lambdas/src/newsletter-sqs-processor/.venv/`
- `lambdas/src/newsletter-api-admin/.venv/`
- `lambdas/src/newsletter-admin-authorizer/.venv/`

**Activating a Virtual Environment:**
```bash
# From project root
cd lambdas/src/newsletter-api-public
source .venv/bin/activate

# Or from lambdas directory
source src/newsletter-api-public/.venv/bin/activate
```

**Installing Dependencies:**
```bash
# Activate the virtual environment first, then:
pip install -r requirements.txt

# For development/testing dependencies:
pip install pytest moto boto3
```

**Running Tests:**
```bash
# Run tests for a specific Lambda function
cd lambdas/src/newsletter-api-public
source .venv/bin/activate
python -m pytest -v
```

**Important Notes:**
- Each Lambda has isolated dependencies defined in its own `requirements.txt`
- Virtual environments are for local development/testing only
- Lambda deployment packages are built by Terraform using Docker (`build_in_docker = true`)
- When running Terraform commands, ensure `AWS_PROFILE=jscom` is set

## Dependencies and Infrastructure

### Remote State Dependencies

This project depends on remote Terraform state from two other projects:

- **jscom-core-infra**: Provides shared infrastructure (Route53, ACM certificates)
- **jscom-blog**: Provides API Gateway instance that this project integrates with
  - `api_gateway_id`
  - `api_gateway_execution_arn`
  - `custom_domain_name` (api.johnsosoka.com)
  - `custom_domain_name_target`

The API Gateway is provisioned in `jscom-blog` project, and this project adds routes/integrations to it.

### AWS Resources

**Lambda Functions:**
- Runtime: Python 3.13 (Amazon Linux 2023)
- Deployment: Built in Docker via terraform-aws-modules/lambda/aws
- Each function has isolated `app/` directory and `requirements.txt`

**DynamoDB Table:**
- `newsletter-subscribers`: Single table design with fields:
  - `id` (hash key, UUID)
  - `email` (string)
  - `name` (string)
  - `status` (string: "active" or "inactive")
  - `subscribed_at` (number: Unix timestamp)
  - `updated_at` (number: Unix timestamp)
  - `ip_address` (string)
  - `user_agent` (string)
  - GSI: `email-index` (hash key: `email`)
  - GSI: `status-index` (hash key: `status`)

**SQS Queue:**
- `newsletter-operations-queue`: Receives subscription operations from public API

## Development Commands

### Terraform

When running terraform locally, ensure the current AWS_PROFILE is jscom.

Navigate to `terraform/` directory for all infrastructure operations:

```bash
cd terraform
export AWS_PROFILE=jscom
terraform init
terraform plan
terraform apply
```

**Note**: Terraform state is managed remotely in S3 bucket `jscom-tf-backend` with DynamoDB locking.

### Testing Lambda Functions

Each Lambda function can be tested independently with its own virtual environment:

```bash
# Test a specific Lambda function
cd lambdas/src/newsletter-api-admin
source .venv/bin/activate
python -m pytest -v
```

### Lambda Deployment

Lambda code is deployed via Terraform. After modifying Lambda source:

```bash
cd terraform
export AWS_PROFILE=jscom
terraform apply
```

Terraform uses `build_in_docker = true` to build Python dependencies for Linux runtime.

## API Specification

### Public Endpoints

**Subscribe to Newsletter:**
- Endpoint: `POST https://api.johnsosoka.com/v1/newsletter`
- Request Body: `{"email": "user@example.com", "name": "John Doe"}`
- Response: `{"message": "Subscription request received. Processing..."}`

**Unsubscribe from Newsletter:**
- Endpoint: `DELETE https://api.johnsosoka.com/v1/newsletter`
- Request Body: `{"email": "user@example.com"}`
- Response: `{"message": "Unsubscribe request received. Processing..."}`

**Check Subscription Status:**
- Endpoint: `GET https://api.johnsosoka.com/v1/newsletter/status?email=user@example.com`
- Response: `{"status": 200, "data": {"email": "user@example.com", "name": "John Doe", "status": "active", "subscribed_at": 1729305600}}`

### Admin Endpoints

All admin endpoints require `x-api-key` header for authentication.

**Get Statistics:**
- Endpoint: `GET https://api.johnsosoka.com/v1/newsletter/admin/stats`
- Response: Statistics about total, active, and inactive subscribers

**List Subscribers:**
- Endpoint: `GET https://api.johnsosoka.com/v1/newsletter/admin/subscribers?limit=50&status=active`
- Response: Paginated list of subscribers with optional status filter

**Get Single Subscriber:**
- Endpoint: `GET https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{id}`
- Response: Single subscriber details

**Update Subscriber:**
- Endpoint: `PATCH https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{id}`
- Request Body: `{"email": "newemail@example.com"}`
- Response: Updated subscriber details

**Remove Subscriber:**
- Endpoint: `DELETE https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{id}`
- Response: Success message

## Key Implementation Details

### Subscription Operations

The `newsletter-api-public` Lambda handles three operations:
1. **POST /v1/newsletter**: Validates email/name, sends operation to SQS with type "subscribe"
2. **DELETE /v1/newsletter**: Validates email, sends operation to SQS with type "unsubscribe"
3. **GET /v1/newsletter/status**: Queries DynamoDB email-index GSI directly for immediate response

### SQS Processing

The `newsletter-sqs-processor` Lambda:
- Receives operations from SQS queue
- For "subscribe": Checks email-index GSI for existing subscription, creates or reactivates subscriber
- For "unsubscribe": Updates status to "inactive" (soft delete)
- Extracts IP address and user agent from operation message
- Sets timestamps: `subscribed_at` (first subscription), `updated_at` (every change)
- Deletes SQS message after successful processing

### Admin API Routing

The `newsletter-api-admin` Lambda uses AWS Lambda Powertools `APIGatewayHttpResolver` for routing:
- Catch-all route pattern: `ANY /v1/newsletter/admin/{proxy+}`
- Pydantic v2 models for request/response validation
- Separate handlers module for business logic
- Pagination support with next_token encoding

### Request Context Extraction

The `newsletter-api-public` Lambda extracts metadata from API Gateway v2 event:
- IP Address: `event['requestContext']['http']['sourceIp']`
- User Agent: `event['requestContext']['http']['userAgent']`

### GSI Usage

**email-index GSI:**
- Used by `newsletter-api-public` for status checks (direct query)
- Used by `newsletter-sqs-processor` for duplicate detection
- Allows efficient queries without scanning entire table

**status-index GSI:**
- Used by `newsletter-api-admin` for filtering by active/inactive status
- Enables efficient admin views and statistics

## Important Notes

- Lambda functions manually delete SQS messages after processing (not automatic)
- Subscribers are soft-deleted (status set to "inactive") to preserve history
- Email addresses are case-insensitive (normalize to lowercase in Lambda)
- API Gateway integration uses `payload_format_version = "2.0"` (API Gateway v2 format)
- Lambda functions use `handler` format: `<filename>.<function_name>` (e.g., `newsletter_api_public_lambda.lambda_handler`)
- Admin authorizer returns simple boolean response (API Gateway v2 simple authorizer format)
