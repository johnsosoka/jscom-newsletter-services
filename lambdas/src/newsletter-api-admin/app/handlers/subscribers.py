"""
Subscriber operation handlers for the admin API.

Provides functions for listing, retrieving, updating, and deleting subscribers.
"""

import os
import boto3
import base64
import json
import time
from typing import Any
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key
from models import Subscriber, SubscriberListResponse, StatsResponse

logger = Logger()

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
subscribers_table_name = os.environ['NEWSLETTER_SUBSCRIBERS_TABLE_NAME']
subscribers_table = dynamodb.Table(subscribers_table_name)


def item_to_subscriber(item: dict[str, Any]) -> Subscriber:
    """
    Convert a DynamoDB item to a Subscriber model.

    Args:
        item: Raw DynamoDB item

    Returns:
        Subscriber domain model
    """
    return Subscriber(
        id=item['id'],
        email=item['email'],
        name=item.get('name', ''),
        status=item.get('status', 'inactive'),
        subscribed_at=int(item.get('subscribed_at', 0)),
        updated_at=int(item.get('updated_at', 0)),
        ip_address=item.get('ip_address', ''),
        user_agent=item.get('user_agent', '')
    )


def list_subscribers(
    limit: int = 50,
    next_token: str | None = None,
    status: str | None = None
) -> SubscriberListResponse:
    """
    List newsletter subscribers with pagination and optional filtering.

    Args:
        limit: Maximum number of subscribers to return (1-100)
        next_token: Pagination token for retrieving next page
        status: Optional filter by status ('active' or 'inactive')

    Returns:
        SubscriberListResponse containing subscribers and pagination info

    Raises:
        Exception: If DynamoDB query fails
    """
    logger.info(f"Listing subscribers: limit={limit}, next_token={next_token}, status={status}")

    try:
        if status:
            # Use status-index GSI if filtering by status
            query_kwargs: dict[str, Any] = {
                'IndexName': 'status-index',
                'KeyConditionExpression': Key('status').eq(status),
                'Limit': limit,
            }

            # Add pagination token if provided
            if next_token:
                try:
                    decoded_token = json.loads(base64.b64decode(next_token).decode('utf-8'))
                    query_kwargs['ExclusiveStartKey'] = decoded_token
                except Exception as e:
                    logger.error(f"Failed to decode pagination token: {e}")
                    raise ValueError("Invalid pagination token")

            response = subscribers_table.query(**query_kwargs)

        else:
            # Scan all subscribers without filter
            scan_kwargs: dict[str, Any] = {
                'Limit': limit,
            }

            # Add pagination token if provided
            if next_token:
                try:
                    decoded_token = json.loads(base64.b64decode(next_token).decode('utf-8'))
                    scan_kwargs['ExclusiveStartKey'] = decoded_token
                except Exception as e:
                    logger.error(f"Failed to decode pagination token: {e}")
                    raise ValueError("Invalid pagination token")

            response = subscribers_table.scan(**scan_kwargs)

        # Convert DynamoDB items to domain models
        subscribers = [item_to_subscriber(item) for item in response.get('Items', [])]

        # Sort by subscribed_at descending (most recent first)
        subscribers.sort(key=lambda x: x.subscribed_at, reverse=True)

        # Encode pagination token if more results available
        encoded_next_token = None
        if 'LastEvaluatedKey' in response:
            token_bytes = json.dumps(response['LastEvaluatedKey']).encode('utf-8')
            encoded_next_token = base64.b64encode(token_bytes).decode('utf-8')

        logger.info(f"Retrieved {len(subscribers)} subscribers")

        return SubscriberListResponse(
            subscribers=subscribers,
            next_token=encoded_next_token,
            count=len(subscribers)
        )

    except Exception as e:
        logger.error(f"Error listing subscribers: {e}")
        raise


def get_subscriber_by_id(subscriber_id: str) -> Subscriber | None:
    """
    Retrieve a specific subscriber by ID.

    Args:
        subscriber_id: The unique subscriber identifier

    Returns:
        Subscriber if found, None otherwise

    Raises:
        Exception: If DynamoDB query fails
    """
    logger.info(f"Retrieving subscriber: {subscriber_id}")

    try:
        response = subscribers_table.get_item(Key={'id': subscriber_id})

        if 'Item' not in response:
            logger.info(f"Subscriber not found: {subscriber_id}")
            return None

        subscriber = item_to_subscriber(response['Item'])
        logger.info(f"Successfully retrieved subscriber: {subscriber_id}")

        return subscriber

    except Exception as e:
        logger.error(f"Error retrieving subscriber: {e}")
        raise


def update_subscriber_email(subscriber_id: str, new_email: str) -> Subscriber | None:
    """
    Update a subscriber's email address.

    Args:
        subscriber_id: The unique subscriber identifier
        new_email: The new email address

    Returns:
        Updated Subscriber if found, None if subscriber doesn't exist

    Raises:
        Exception: If DynamoDB update fails
    """
    logger.info(f"Updating subscriber {subscriber_id} email to {new_email}")

    try:
        # First check if subscriber exists
        existing = get_subscriber_by_id(subscriber_id)
        if not existing:
            return None

        # Update email and updated_at timestamp
        current_timestamp = int(time.time())
        response = subscribers_table.update_item(
            Key={'id': subscriber_id},
            UpdateExpression='SET email = :email, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':email': new_email,
                ':timestamp': current_timestamp
            },
            ReturnValues='ALL_NEW'
        )

        updated_subscriber = item_to_subscriber(response['Attributes'])
        logger.info(f"Successfully updated subscriber {subscriber_id}")

        return updated_subscriber

    except Exception as e:
        logger.error(f"Error updating subscriber: {e}")
        raise


def delete_subscriber(subscriber_id: str) -> bool:
    """
    Delete a subscriber (hard delete).

    Args:
        subscriber_id: The unique subscriber identifier

    Returns:
        True if subscriber was deleted, False if not found

    Raises:
        Exception: If DynamoDB delete fails
    """
    logger.info(f"Deleting subscriber: {subscriber_id}")

    try:
        # Check if subscriber exists first
        existing = get_subscriber_by_id(subscriber_id)
        if not existing:
            logger.info(f"Subscriber not found for deletion: {subscriber_id}")
            return False

        # Delete the subscriber
        subscribers_table.delete_item(Key={'id': subscriber_id})
        logger.info(f"Successfully deleted subscriber: {subscriber_id}")

        return True

    except Exception as e:
        logger.error(f"Error deleting subscriber: {e}")
        raise


def get_stats() -> StatsResponse:
    """
    Calculate and return statistics about the newsletter system.

    Computes metrics including total subscribers, active/inactive counts,
    and recent subscription activity.

    Returns:
        StatsResponse containing system statistics

    Raises:
        Exception: If DynamoDB queries fail
    """
    logger.info("Calculating system statistics")

    try:
        # Scan all subscribers
        subscribers_response = subscribers_table.scan()
        all_subscribers = subscribers_response['Items']

        # Handle pagination if there are more subscribers
        while 'LastEvaluatedKey' in subscribers_response:
            subscribers_response = subscribers_table.scan(
                ExclusiveStartKey=subscribers_response['LastEvaluatedKey']
            )
            all_subscribers.extend(subscribers_response['Items'])

        # Calculate statistics
        total_subscribers = len(all_subscribers)
        active_count = sum(1 for sub in all_subscribers if sub.get('status') == 'active')
        inactive_count = total_subscribers - active_count

        # Calculate recent subscriptions (last 24 hours)
        current_time = int(time.time())
        twenty_four_hours_ago = current_time - (24 * 60 * 60)
        recent_24h = sum(
            1 for sub in all_subscribers
            if int(sub.get('subscribed_at', 0)) >= twenty_four_hours_ago
        )

        stats = StatsResponse(
            total_subscribers=total_subscribers,
            active_count=active_count,
            inactive_count=inactive_count,
            recent_24h=recent_24h,
        )

        logger.info(f"Stats calculated: {stats.model_dump()}")

        return stats

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise
