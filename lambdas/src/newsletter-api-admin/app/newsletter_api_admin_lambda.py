"""
Admin API Lambda function for managing newsletter subscribers.

This Lambda provides REST API endpoints for administrative operations on the
newsletter system, including viewing subscribers, managing subscriptions, and
retrieving system statistics.

Environment Variables:
    NEWSLETTER_SUBSCRIBERS_TABLE_NAME: DynamoDB table for newsletter subscribers
"""

import json
from typing import Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths
from pydantic import ValidationError

from models import (
    ApiResponse,
    Subscriber,
    SubscriberListResponse,
    StatsResponse,
    SubscriberListQueryParams,
    UpdateSubscriberRequest,
)
from handlers import (
    list_subscribers,
    get_subscriber_by_id,
    update_subscriber_email,
    delete_subscriber,
    get_stats,
)

# Initialize logger and API resolver
logger = Logger()
app = APIGatewayHttpResolver()


@app.get("/v1/newsletter/admin/subscribers")
def handle_list_subscribers() -> dict[str, Any]:
    """
    List newsletter subscribers with pagination.

    Query Parameters:
        limit (int): Max subscribers per page (1-100, default 50)
        next_token (str): Pagination token for next page
        status (str): Filter by 'active' or 'inactive'

    Returns:
        200: SubscriberListResponse with subscribers and pagination
        400: Validation error
        500: Internal server error
    """
    try:
        # Parse query parameters
        query_params = SubscriberListQueryParams(
            limit=int(app.current_event.get_query_string_value("limit", "50")),
            next_token=app.current_event.get_query_string_value("next_token"),
            status=app.current_event.get_query_string_value("status"),
        )

        # Get subscribers
        result: SubscriberListResponse = list_subscribers(
            limit=query_params.limit,
            next_token=query_params.next_token,
            status=query_params.status,
        )

        response = ApiResponse[SubscriberListResponse](
            status=200,
            data=result
        )

        return response.model_dump()

    except ValidationError as e:
        logger.error(f"Validation error in list_subscribers: {e}")
        response = ApiResponse[None](
            status=400,
            error=f"Validation error: {str(e)}"
        )
        return response.model_dump()

    except ValueError as e:
        logger.error(f"Value error in list_subscribers: {e}")
        response = ApiResponse[None](
            status=400,
            error=str(e)
        )
        return response.model_dump()

    except Exception as e:
        logger.exception(f"Error in list_subscribers: {e}")
        response = ApiResponse[None](
            status=500,
            error="Internal server error"
        )
        return response.model_dump()


@app.get("/v1/newsletter/admin/subscribers/<subscriber_id>")
def handle_get_subscriber(subscriber_id: str) -> dict[str, Any]:
    """
    Retrieve a specific subscriber by ID.

    Path Parameters:
        subscriber_id (str): Unique subscriber identifier

    Returns:
        200: Subscriber details
        404: Subscriber not found
        500: Internal server error
    """
    try:
        subscriber: Subscriber | None = get_subscriber_by_id(subscriber_id)

        if subscriber is None:
            response = ApiResponse[None](
                status=404,
                error=f"Subscriber not found: {subscriber_id}"
            )
            return response.model_dump()

        response = ApiResponse(
            status=200,
            data=subscriber
        )

        return json.loads(response.model_dump_json())

    except Exception as e:
        logger.exception(f"Error in get_subscriber: {e}")
        response = ApiResponse[None](
            status=500,
            error="Internal server error"
        )
        return response.model_dump()


@app.get("/v1/newsletter/admin/stats")
def handle_get_stats() -> dict[str, Any]:
    """
    Get system statistics and analytics.

    Returns:
        200: StatsResponse with system metrics
        500: Internal server error
    """
    try:
        stats: StatsResponse = get_stats()

        response = ApiResponse[StatsResponse](
            status=200,
            data=stats
        )

        return response.model_dump()

    except Exception as e:
        logger.exception(f"Error in get_stats: {e}")
        response = ApiResponse[None](
            status=500,
            error="Internal server error"
        )
        return response.model_dump()


@app.patch("/v1/newsletter/admin/subscribers/<subscriber_id>")
def handle_update_subscriber(subscriber_id: str) -> dict[str, Any]:
    """
    Update a subscriber's email address.

    Path Parameters:
        subscriber_id (str): Unique subscriber identifier

    Request Body:
        {
            "email": "newemail@example.com"
        }

    Returns:
        200: Updated Subscriber details
        400: Validation error
        404: Subscriber not found
        500: Internal server error
    """
    try:
        # Parse request body
        body: dict[str, Any] = app.current_event.json_body
        request: UpdateSubscriberRequest = UpdateSubscriberRequest(**body)

        # Update subscriber
        updated_subscriber: Subscriber | None = update_subscriber_email(
            subscriber_id,
            request.email
        )

        if updated_subscriber is None:
            response = ApiResponse[None](
                status=404,
                error=f"Subscriber not found: {subscriber_id}"
            )
            return response.model_dump()

        response = ApiResponse(
            status=200,
            data=updated_subscriber
        )

        return json.loads(response.model_dump_json())

    except ValidationError as e:
        logger.error(f"Validation error in update_subscriber: {e}")
        response = ApiResponse[None](
            status=400,
            error=f"Validation error: {str(e)}"
        )
        return response.model_dump()

    except Exception as e:
        logger.exception(f"Error in update_subscriber: {e}")
        response = ApiResponse[None](
            status=500,
            error="Internal server error"
        )
        return response.model_dump()


@app.delete("/v1/newsletter/admin/subscribers/<subscriber_id>")
def handle_delete_subscriber(subscriber_id: str) -> dict[str, Any]:
    """
    Delete a subscriber (hard delete).

    Path Parameters:
        subscriber_id (str): Unique subscriber identifier

    Returns:
        200: Success message
        404: Subscriber not found
        500: Internal server error
    """
    try:
        success: bool = delete_subscriber(subscriber_id)

        if not success:
            response = ApiResponse[None](
                status=404,
                error=f"Subscriber not found: {subscriber_id}"
            )
            return response.model_dump()

        response = ApiResponse(
            status=200,
            data={"message": "Subscriber deleted successfully"}
        )

        return response.model_dump()

    except Exception as e:
        logger.exception(f"Error in delete_subscriber: {e}")
        response = ApiResponse[None](
            status=500,
            error="Internal server error"
        )
        return response.model_dump()


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler for admin API requests.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context object

    Returns:
        API Gateway response with status code and body
    """
    logger.info(f"Received event: {json.dumps(event)}")

    return app.resolve(event, context)
