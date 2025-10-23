"""
SQS-triggered Lambda function for processing newsletter subscription operations.

This Lambda processes subscription and unsubscription operations from the
newsletter-operations-queue SQS queue and updates the DynamoDB subscribers table.

Environment Variables:
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME: DynamoDB table for subscribers
"""

import json
import os
import logging
from typing import Any
from datetime import datetime
from uuid import uuid4

import boto3
from pydantic import BaseModel, EmailStr, Field, ValidationError
from boto3.dynamodb.conditions import Key

# Initialize logger and AWS clients
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Get environment variables
subscribers_table_name = os.environ['NEWSLETTER_SUBSCRIBERS_TABLE_NAME']
subscribers_table = dynamodb.Table(subscribers_table_name)


class OperationMessage(BaseModel):
    """
    Model for subscription operation messages from SQS.

    Attributes:
        operation: Type of operation ('subscribe' or 'unsubscribe')
        email: Subscriber email address
        name: Subscriber name (required for subscribe, optional for unsubscribe)
        ip_address: IP address from the request
        user_agent: User agent from the request
        timestamp: Unix timestamp when the operation was requested
    """
    operation: str = Field(description="Operation type: 'subscribe' or 'unsubscribe'")
    email: EmailStr = Field(description="Subscriber email address")
    name: str | None = Field(default=None, description="Subscriber name")
    ip_address: str = Field(description="Request IP address")
    user_agent: str = Field(description="Request user agent")
    timestamp: int = Field(description="Operation request timestamp")


def query_subscriber_by_email(email: str) -> dict[str, Any] | None:
    """
    Query subscriber by email using the email-index GSI.

    Args:
        email: Email address to query

    Returns:
        Subscriber item if found, None otherwise

    Raises:
        Exception: If DynamoDB query fails
    """
    try:
        response = subscribers_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )

        items = response.get('Items', [])
        return items[0] if items else None

    except Exception as e:
        logger.error(f"Error querying subscriber by email: {e}")
        raise


def process_subscribe_operation(message: OperationMessage) -> None:
    """
    Process a subscription operation.

    Behavior:
    - If subscriber exists and is inactive: reactivate (set status='active', update updated_at)
    - If subscriber exists and is active: only update updated_at
    - If subscriber does not exist: create new with status='active'

    Args:
        message: Subscription operation message

    Raises:
        Exception: If DynamoDB operation fails
    """
    current_timestamp = int(datetime.utcnow().timestamp())

    logger.info(f"Processing subscribe operation for email: {message.email}")

    # Check if subscriber exists
    existing_subscriber = query_subscriber_by_email(message.email)

    if existing_subscriber:
        subscriber_id = existing_subscriber['id']
        current_status = existing_subscriber.get('status', 'inactive')

        logger.info(f"Subscriber exists with ID {subscriber_id} and status {current_status}")

        if current_status == 'inactive':
            # Reactivate subscriber
            subscribers_table.update_item(
                Key={'id': subscriber_id},
                UpdateExpression='SET #status = :active_status, updated_at = :timestamp',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':active_status': 'active',
                    ':timestamp': current_timestamp
                }
            )
            logger.info(f"Reactivated subscriber {subscriber_id}")

        else:
            # Already active, just update timestamp
            subscribers_table.update_item(
                Key={'id': subscriber_id},
                UpdateExpression='SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': current_timestamp
                }
            )
            logger.info(f"Updated timestamp for active subscriber {subscriber_id}")

    else:
        # Create new subscriber
        subscriber_id = str(uuid4())
        new_subscriber = {
            'id': subscriber_id,
            'email': message.email,
            'name': message.name,
            'status': 'active',
            'subscribed_at': current_timestamp,
            'updated_at': current_timestamp,
            'ip_address': message.ip_address,
            'user_agent': message.user_agent
        }

        subscribers_table.put_item(Item=new_subscriber)
        logger.info(f"Created new subscriber with ID {subscriber_id}")


def process_unsubscribe_operation(message: OperationMessage) -> None:
    """
    Process an unsubscription operation.

    Behavior:
    - Query by email
    - If found: set status='inactive', update updated_at
    - If not found: log and skip (already unsubscribed or never existed)

    Args:
        message: Unsubscription operation message

    Raises:
        Exception: If DynamoDB operation fails
    """
    current_timestamp = int(datetime.utcnow().timestamp())

    logger.info(f"Processing unsubscribe operation for email: {message.email}")

    # Check if subscriber exists
    existing_subscriber = query_subscriber_by_email(message.email)

    if existing_subscriber:
        subscriber_id = existing_subscriber['id']

        # Set status to inactive
        subscribers_table.update_item(
            Key={'id': subscriber_id},
            UpdateExpression='SET #status = :inactive_status, updated_at = :timestamp',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':inactive_status': 'inactive',
                ':timestamp': current_timestamp
            }
        )
        logger.info(f"Unsubscribed subscriber {subscriber_id}")

    else:
        logger.info(f"Subscriber not found for email {message.email}, skipping unsubscribe")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler for processing SQS subscription operation messages.

    Args:
        event: SQS event containing one or more messages
        context: Lambda context object

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} messages")

    processed_count = 0
    failed_count = 0
    failed_messages = []

    for record in event.get('Records', []):
        receipt_handle = record.get('receiptHandle')
        message_body = record.get('body')

        try:
            # Parse message body
            message_data = json.loads(message_body)
            operation_message = OperationMessage(**message_data)

            # Process based on operation type
            if operation_message.operation == 'subscribe':
                process_subscribe_operation(operation_message)
            elif operation_message.operation == 'unsubscribe':
                process_unsubscribe_operation(operation_message)
            else:
                logger.warning(f"Unknown operation type: {operation_message.operation}")
                failed_count += 1
                continue

            # Message processed successfully
            processed_count += 1
            logger.info(f"Successfully processed {operation_message.operation} for {operation_message.email}")

        except ValidationError as e:
            logger.error(f"Validation error processing message: {e}")
            failed_count += 1
            failed_messages.append({
                'receipt_handle': receipt_handle,
                'error': str(e)
            })

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            failed_count += 1
            failed_messages.append({
                'receipt_handle': receipt_handle,
                'error': str(e)
            })

    logger.info(f"Processing complete. Processed: {processed_count}, Failed: {failed_count}")

    return {
        'statusCode': 200,
        'processed': processed_count,
        'failed': failed_count,
        'failed_messages': failed_messages
    }
