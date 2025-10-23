# JSCOM Newsletter Services

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Terraform](https://img.shields.io/badge/Terraform-1.0+-purple.svg)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-Serverless-orange.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Serverless newsletter management API built on AWS Lambda, API Gateway, SQS, and DynamoDB. Provides public subscription endpoints and authenticated admin management capabilities with a hybrid architecture for optimal performance.

## Features

- **Public Subscription API** - Simple REST endpoints for subscribe/unsubscribe operations
- **Admin Management API** - Full CRUD operations with API key authentication
- **Async Processing** - SQS-based queue for reliable subscription processing
- **Direct Status Checks** - Fast DynamoDB queries via GSI for instant status lookups
- **Soft Deletes** - Preserves subscription history for analytics
- **Type Safety** - Pydantic v2 models throughout for robust validation
- **Production Ready** - Comprehensive error handling, logging, and monitoring

## Quick Start

**Subscribe to newsletter:**
```bash
curl -X POST https://api.johnsosoka.com/v1/newsletter \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "John Doe"}'
```

**Check subscription status:**
```bash
curl "https://api.johnsosoka.com/v1/newsletter/status?email=user@example.com"
```

## Table of Contents

- [Architecture](#architecture)
- [Resources](#resources)
- [API Methods](#api-methods)
- [Deployment](#deployment)
- [Security](#security)
- [Development](#development)
- [Postman Collection](#postman-collection)
- [License](#license)

## Architecture

Event-driven serverless architecture with four Lambda functions:

### Public API Flow
1. **API Gateway** → `newsletter-api-public` Lambda
   - POST `/v1/newsletter` - Subscribe to newsletter (async via SQS)
   - DELETE `/v1/newsletter` - Unsubscribe from newsletter (async via SQS)
   - GET `/v1/newsletter/status?email=...` - Check subscription status (direct DynamoDB read)

2. **newsletter-operations-queue** → `newsletter-sqs-processor` Lambda
   - Processes signup/removal operations asynchronously
   - Writes to `newsletter-subscribers` DynamoDB table
   - Sets status (active/inactive) with timestamps

### Admin API Flow
1. Admin requests sent to API Gateway at `/v1/newsletter/admin/*` endpoints
2. API Gateway invokes `newsletter-admin-authorizer` Lambda to validate `x-api-key` header
3. If authorized, request routed to `newsletter-api-admin` Lambda
4. Admin Lambda performs CRUD operations on DynamoDB
5. Results returned as JSON responses

## Resources

### Lambda Functions

All Lambda functions written in Python 3.13 using AWS Lambda Powertools.

#### Public API Lambda
- **`newsletter-api-public`**: Handles public subscription endpoints. Uses Lambda Powertools for routing. Async operations (signup/unsubscribe) send to SQS. Status checks query DynamoDB directly via email GSI.

#### Worker Lambda
- **`newsletter-sqs-processor`**: Event-driven function triggered by SQS. Processes subscription operations, writes to DynamoDB with timestamps, manages subscriber status.

#### Admin API Lambdas
- **`newsletter-api-admin`**: REST API Lambda for admin operations. Uses Lambda Powertools for routing, Pydantic v2 for validation. Supports pagination, filtering, and statistics.

- **`newsletter-admin-authorizer`**: Custom Lambda authorizer for API Gateway v2. Validates `x-api-key` header against environment variable.

### DynamoDB Table

**newsletter-subscribers**: Single table design storing all subscriber data
- Hash key: `id` (UUID)
- Attributes: `email`, `name`, `status`, `subscribed_at`, `updated_at`, `ip_address`, `user_agent`
- GSI: `email-index` - Query by email for status checks and duplicate prevention
- GSI: `status-index` - Filter by status (active/inactive) for admin views

### SQS Queue

- `newsletter-operations-queue`: Receives signup/removal operations from public API for async processing

## API Methods

### Public Endpoints

#### Subscribe to Newsletter
- `POST https://api.johnsosoka.com/v1/newsletter`

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "message": "Subscription request received. Processing..."
}
```

#### Unsubscribe from Newsletter
- `DELETE https://api.johnsosoka.com/v1/newsletter`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Unsubscribe request received. Processing..."
}
```

#### Check Subscription Status
- `GET https://api.johnsosoka.com/v1/newsletter/status?email=user@example.com`

**Response:**
```json
{
  "status": 200,
  "data": {
    "email": "user@example.com",
    "name": "John Doe",
    "status": "active",
    "subscribed_at": 1729305600
  }
}
```

### Admin Endpoints

All admin endpoints require authentication via API key in the `x-api-key` header.

#### Get Newsletter Statistics
- `GET https://api.johnsosoka.com/v1/newsletter/admin/stats`

**Headers:**
```
x-api-key: <your-api-key>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "total_subscribers": 1250,
    "active_subscribers": 1180,
    "inactive_subscribers": 70,
    "recent_signups_24h": 15
  }
}
```

#### List Subscribers
- `GET https://api.johnsosoka.com/v1/newsletter/admin/subscribers?limit=50&status=active`

**Query Parameters:**
- `limit` (optional): Number of subscribers per page (1-100, default: 50)
- `next_token` (optional): Pagination token from previous response
- `status` (optional): Filter by status (`active` or `inactive`)

**Headers:**
```
x-api-key: <your-api-key>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "subscribers": [
      {
        "id": "uuid-string",
        "email": "user@example.com",
        "name": "John Doe",
        "status": "active",
        "subscribed_at": 1729305600,
        "updated_at": 1729305600,
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
      }
    ],
    "next_token": "base64-encoded-token",
    "total_count": 1250
  }
}
```

#### Get Single Subscriber
- `GET https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{subscriber_id}`

**Headers:**
```
x-api-key: <your-api-key>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "name": "John Doe",
    "status": "active",
    "subscribed_at": 1729305600,
    "updated_at": 1729305600
  }
}
```

#### Update Subscriber Email
- `PATCH https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{subscriber_id}`

**Headers:**
```
x-api-key: <your-api-key>
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "newemail@example.com"
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "id": "uuid-string",
    "email": "newemail@example.com",
    "name": "John Doe",
    "status": "active",
    "updated_at": 1729310000
  }
}
```

#### Remove Subscriber
- `DELETE https://api.johnsosoka.com/v1/newsletter/admin/subscribers/{subscriber_id}`

**Headers:**
```
x-api-key: <your-api-key>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "message": "Subscriber removed successfully"
  }
}
```

## Deployment

### Prerequisites

1. AWS CLI configured with `jscom` profile
2. Terraform installed (v1.0+)
3. API key for admin endpoints (generate with `openssl rand -hex 32`)

### Configuration

Create a `terraform.tfvars` file in the `terraform/` directory:

```hcl
admin_api_key_value = "your-secure-api-key-here"
```

**Security Note**: Never commit `terraform.tfvars` to version control.

### Deploy

Navigate to the `terraform` directory and run:

```bash
cd terraform
export AWS_PROFILE=jscom

# Initialize Terraform (first time only)
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### Lambda Deployment

Lambda functions are built and deployed automatically by Terraform:
- Python dependencies installed in Docker containers for Linux compatibility
- Functions target x86_64 architecture
- Source code changes trigger automatic redeployment

### Testing Deployment

Test the public API:
```bash
# Subscribe
curl -X POST https://api.johnsosoka.com/v1/newsletter \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test User"}'

# Check status
curl -X GET "https://api.johnsosoka.com/v1/newsletter/status?email=test@example.com"

# Unsubscribe
curl -X DELETE https://api.johnsosoka.com/v1/newsletter \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

Test the admin API:
```bash
curl -X GET https://api.johnsosoka.com/v1/newsletter/admin/stats \
  -H "x-api-key: your-api-key-here"
```

## Security

### API Key Management

Admin API key managed as Terraform variable and stored as environment variable in Lambda authorizer. Best practices:
- Generate strong API keys: `openssl rand -hex 32`
- Store in `terraform.tfvars` (excluded from git)
- Rotate keys periodically by updating Terraform variable and redeploying
- Monitor CloudWatch logs for unauthorized access attempts

### IAM Permissions

Lambda functions follow principle of least privilege:
- `newsletter-api-public`: SQS SendMessage, DynamoDB Query on email-index GSI
- `newsletter-sqs-processor`: SQS ReceiveMessage/DeleteMessage, DynamoDB Read/Write
- `newsletter-api-admin`: DynamoDB Read/Write on newsletter-subscribers table only
- `newsletter-admin-authorizer`: No AWS permissions (reads environment variable)

### Network Security

- All API endpoints use HTTPS (enforced by API Gateway)
- Admin endpoints protected by Lambda authorizer
- No public IP addresses or VPC required (serverless architecture)

## Development

### Python Virtual Environments

Each Lambda has its own isolated virtual environment for local development:

```bash
cd lambdas/src/newsletter-api-public
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running Tests

```bash
cd lambdas/src/newsletter-api-public
source .venv/bin/activate
python -m pytest test/ -v
```

## Postman Collection

A complete Postman collection is available in the `postman/` directory for easy API testing.

### Import Collection

1. Open Postman
2. Click **Import** → Select `postman/jscom-newsletter-services.postman_collection.json`
3. Configure the `admin_api_key` variable in the collection settings

The collection includes:
- **Public Endpoints** - Subscribe, Unsubscribe, Check Status
- **Admin Endpoints** - Statistics, List/Get/Update/Delete Subscribers

See [postman/README.md](postman/README.md) for detailed usage instructions.

## Project Structure

```
jscom-newsletter-services/
├── lambdas/
│   └── src/
│       ├── newsletter-api-public/      # Public API Lambda
│       ├── newsletter-api-admin/       # Admin API Lambda
│       ├── newsletter-sqs-processor/   # SQS worker Lambda
│       └── newsletter-admin-authorizer/ # API key authorizer
├── terraform/                          # Infrastructure as Code
│   ├── main.tf
│   ├── lambdas.tf
│   ├── api-gateway.tf
│   ├── dynamoDB.tf
│   └── sqs.tf
├── postman/                            # Postman collection for testing
├── CLAUDE.md                           # AI assistant guidance
└── README.md
```

## Related Projects

This project is part of the johnsosoka.com infrastructure:
- [jscom-blog](https://github.com/johnsosoka/jscom-blog) - Main blog and API Gateway
- [jscom-contact-services](https://github.com/johnsosoka/jscom-contact-services) - Contact form API
- [jscom-core-infrastructure](https://github.com/johnsosoka/jscom-core-infrastructure) - Shared AWS resources

## License

MIT License - see LICENSE file for details
