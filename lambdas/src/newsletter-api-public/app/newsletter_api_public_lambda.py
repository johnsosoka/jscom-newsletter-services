"""
Public API Lambda function for newsletter subscription operations.

This Lambda provides REST API endpoints for newsletter subscription management,
including subscribing, unsubscribing, and checking subscription status.

Environment Variables:
    NEWSLETTER_OPERATIONS_QUEUE_URL: SQS queue URL for operations
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME: DynamoDB table for subscribers
"""

import json
import os
import logging
from typing import Any
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths
from pydantic import BaseModel, EmailStr, Field, ValidationError

# Initialize logger and AWS clients
logger = Logger()
app = APIGatewayHttpResolver()

sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
queue_url = os.environ['NEWSLETTER_OPERATIONS_QUEUE_URL']
subscribers_table_name = os.environ['NEWSLETTER_SUBSCRIBERS_TABLE_NAME']
subscribers_table = dynamodb.Table(subscribers_table_name)


class SubscribeRequest(BaseModel):
    """
    Request model for newsletter subscription.

    Attributes:
        email: Subscriber email address
        name: Subscriber name
    """
    email: EmailStr = Field(description="Subscriber email address")
    name: str = Field(min_length=1, max_length=200, description="Subscriber name")


class UnsubscribeRequest(BaseModel):
    """
    Request model for newsletter unsubscription.

    Attributes:
        email: Subscriber email address to unsubscribe
    """
    email: EmailStr = Field(description="Subscriber email address")


class StatusResponse(BaseModel):
    """
    Response model for subscription status.

    Attributes:
        email: Subscriber email address
        status: Subscription status ('active', 'inactive', or 'not_found')
        subscribed_at: Unix timestamp when subscribed (if found)
        updated_at: Unix timestamp of last update (if found)
    """
    email: str = Field(description="Subscriber email address")
    status: str = Field(description="Subscription status")
    subscribed_at: int | None = Field(default=None, description="Unix timestamp when subscribed")
    updated_at: int | None = Field(default=None, description="Unix timestamp of last update")


class ApiResponse(BaseModel):
    """
    Generic API response wrapper.

    Attributes:
        message: Response message
        error: Error message if request failed
    """
    message: str | None = Field(default=None, description="Response message")
    error: str | None = Field(default=None, description="Error message")


def extract_request_metadata(event: dict[str, Any]) -> dict[str, str]:
    """
    Extract IP address and user agent from API Gateway v2 event.

    Args:
        event: API Gateway HTTP API event

    Returns:
        Dictionary containing ip_address and user_agent
    """
    request_context = event.get('requestContext', {})
    http_context = request_context.get('http', {})

    return {
        'ip_address': http_context.get('sourceIp', 'unknown'),
        'user_agent': http_context.get('userAgent', 'unknown')
    }


def send_operation_to_queue(
    operation: str,
    email: str,
    name: str | None,
    metadata: dict[str, str]
) -> None:
    """
    Send a subscription operation message to SQS.

    Args:
        operation: Operation type ('subscribe' or 'unsubscribe')
        email: Subscriber email address
        name: Subscriber name (optional for unsubscribe)
        metadata: Request metadata (ip_address, user_agent)

    Raises:
        Exception: If SQS send fails
    """
    message = {
        'operation': operation,
        'email': email,
        'name': name,
        'ip_address': metadata['ip_address'],
        'user_agent': metadata['user_agent'],
        'timestamp': int(datetime.utcnow().timestamp())
    }

    logger.info(f"Sending {operation} operation to queue: {email}")

    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f"Failed to send message to SQS: {response}")

    logger.info(f"Successfully sent {operation} operation to queue")


@app.post("/v1/newsletter")
def handle_subscribe() -> dict[str, Any]:
    """
    Handle newsletter subscription requests.

    Request Body:
        {
            "email": "user@example.com",
            "name": "John Doe"
        }

    Returns:
        200: Success message
        400: Validation error
        500: Internal server error
    """
    try:
        # Parse request body
        body: dict[str, Any] = app.current_event.json_body
        request = SubscribeRequest(**body)

        # Extract request metadata
        metadata = extract_request_metadata(app.current_event.raw_event)

        # Send to SQS for processing
        send_operation_to_queue(
            operation='subscribe',
            email=request.email,
            name=request.name,
            metadata=metadata
        )

        response = ApiResponse(
            message="Subscription request received. You will be subscribed shortly."
        )

        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }

    except ValidationError as e:
        logger.error(f"Validation error in subscribe: {e}")
        response = ApiResponse(
            error=f"Validation error: {str(e)}"
        )
        return {
            'statusCode': 400,
            'body': response.model_dump_json()
        }

    except Exception as e:
        logger.exception(f"Error in subscribe: {e}")
        response = ApiResponse(
            error="Internal server error"
        )
        return {
            'statusCode': 500,
            'body': response.model_dump_json()
        }


@app.delete("/v1/newsletter")
def handle_unsubscribe() -> dict[str, Any]:
    """
    Handle newsletter unsubscription requests.

    Request Body:
        {
            "email": "user@example.com"
        }

    Returns:
        200: Success message
        400: Validation error
        500: Internal server error
    """
    try:
        # Parse request body
        body: dict[str, Any] = app.current_event.json_body
        request = UnsubscribeRequest(**body)

        # Extract request metadata
        metadata = extract_request_metadata(app.current_event.raw_event)

        # Send to SQS for processing
        send_operation_to_queue(
            operation='unsubscribe',
            email=request.email,
            name=None,
            metadata=metadata
        )

        response = ApiResponse(
            message="Unsubscription request received. You will be unsubscribed shortly."
        )

        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }

    except ValidationError as e:
        logger.error(f"Validation error in unsubscribe: {e}")
        response = ApiResponse(
            error=f"Validation error: {str(e)}"
        )
        return {
            'statusCode': 400,
            'body': response.model_dump_json()
        }

    except Exception as e:
        logger.exception(f"Error in unsubscribe: {e}")
        response = ApiResponse(
            error="Internal server error"
        )
        return {
            'statusCode': 500,
            'body': response.model_dump_json()
        }


@app.get("/v1/newsletter/status")
def handle_status() -> dict[str, Any]:
    """
    Check subscription status by email.

    Query Parameters:
        email: Email address to check

    Returns:
        200: StatusResponse with subscription details
        400: Validation error (missing or invalid email)
        500: Internal server error
    """
    try:
        # Get email from query parameters
        email = app.current_event.get_query_string_value("email")

        if not email:
            response = ApiResponse(
                error="Email query parameter is required"
            )
            return {
                'statusCode': 400,
                'body': response.model_dump_json()
            }

        # Validate email format
        try:
            validated_email = EmailStr._validate(email)
        except Exception:
            response = ApiResponse(
                error="Invalid email format"
            )
            return {
                'statusCode': 400,
                'body': response.model_dump_json()
            }

        logger.info(f"Checking status for email: {email}")

        # Query email-index GSI
        result = subscribers_table.query(
            IndexName='email-index',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )

        items = result.get('Items', [])

        if not items:
            # Email not found
            status_response = StatusResponse(
                email=email,
                status='not_found'
            )
        else:
            # Get the first (and should be only) result
            subscriber = items[0]
            status_response = StatusResponse(
                email=email,
                status=subscriber.get('status', 'unknown'),
                subscribed_at=subscriber.get('subscribed_at'),
                updated_at=subscriber.get('updated_at')
            )

        return {
            'statusCode': 200,
            'body': status_response.model_dump_json()
        }

    except Exception as e:
        logger.exception(f"Error in status check: {e}")
        response = ApiResponse(
            error="Internal server error"
        )
        return {
            'statusCode': 500,
            'body': response.model_dump_json()
        }


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler for public newsletter API requests.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context object

    Returns:
        API Gateway response with status code and body
    """
    logger.info(f"Received event: {json.dumps(event)}")

    return app.resolve(event, context)
