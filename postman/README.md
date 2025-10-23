# Newsletter Services Postman Collection

This directory contains the Postman collection for testing the jscom-newsletter-services API.

## Collection File

- `jscom-newsletter-services.postman_collection.json` - Complete API collection with public and admin endpoints

## Import Instructions

1. Open Postman
2. Click "Import" button in the top-left corner
3. Select the `jscom-newsletter-services.postman_collection.json` file
4. The collection will be imported with all requests organized into folders

## Configuration

After importing, you need to configure the admin API key:

1. Click on the collection name in Postman
2. Go to the "Variables" tab
3. Update the `admin_api_key` value with your actual API key
4. Click "Save"

Alternatively, you can set the API key for each request individually by editing the `x-api-key` header.

## Collection Structure

### Public Endpoints Folder
These endpoints don't require authentication:

- **Subscribe to Newsletter** - POST request to add a new subscriber
- **Unsubscribe from Newsletter** - DELETE request to remove a subscriber
- **Check Subscription Status** - GET request to check if an email is subscribed

### Admin Folder
These endpoints require authentication via `x-api-key` header:

- **Get Newsletter Statistics** - Get overall subscriber stats
- **List All Subscribers** - List all subscribers with pagination
- **List Active Subscribers** - Filter by active status
- **List Inactive Subscribers** - Filter by inactive status
- **Get Single Subscriber** - Get details for a specific subscriber ID
- **Update Subscriber Email** - Change a subscriber's email address
- **Remove Subscriber** - Delete a subscriber record

## Usage Tips

### Testing Public Endpoints

1. Start with "Subscribe to Newsletter"
2. Copy the email address from the request
3. Use "Check Subscription Status" to verify the subscription
4. Wait a few seconds for async processing (SQS → Lambda)
5. Test "Unsubscribe from Newsletter" with the same email

### Testing Admin Endpoints

1. Make sure `admin_api_key` variable is set correctly
2. Use "Get Newsletter Statistics" to see overall counts
3. Use "List All Subscribers" to see all subscribers
4. Copy a subscriber ID from the response
5. Use "Get Single Subscriber" with the copied ID
6. Test "Update Subscriber Email" or "Remove Subscriber" as needed

### Query Parameters

Some requests have optional query parameters that are disabled by default:
- `next_token` - For pagination (copy from previous response)
- `status` - Filter by active/inactive (enabled in dedicated requests)
- `limit` - Number of results per page (default: 50)

To enable a disabled parameter, check the box next to it in the Params tab.

## Variables

The collection uses the following variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `admin_api_key` | API key for admin endpoints | `your-api-key-here` |

## API Base URL

All requests use: `https://api.johnsosoka.com`

## Common Response Formats

### Public Endpoints
```json
{
  "statusCode": 200,
  "body": "{\"message\":\"Subscription request received...\"}"
}
```

### Admin Endpoints
```json
{
  "status": 200,
  "data": { /* response data */ },
  "error": null
}
```

## Troubleshooting

### Unauthorized Error
- Check that `admin_api_key` variable is set correctly
- Verify the API key matches the one deployed in Terraform

### 404 Not Found
- Ensure the API Gateway and Lambda functions are deployed
- Check the base URL is correct: `https://api.johnsosoka.com`

### Empty Response on Status Check
- The email may not exist in the database
- Make sure to subscribe first before checking status
- Wait a few seconds for async processing to complete

## Related Documentation

- [Main README](../README.md) - Full API documentation
- [Terraform Deployment Guide](../terraform/README.md) - Deployment instructions
