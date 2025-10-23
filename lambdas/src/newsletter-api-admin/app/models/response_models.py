"""
Response models for admin API endpoints.

These models define the structure of API responses with consistent formatting.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from models.subscriber_models import Subscriber


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper providing consistent structure.

    Attributes:
        status: HTTP status code
        data: Response payload (type varies by endpoint)
        error: Error message if request failed
    """

    status: int = Field(description="HTTP status code")
    data: T | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message")


class SubscriberListResponse(BaseModel):
    """
    Response for subscriber listing endpoint with pagination support.

    Attributes:
        subscribers: List of subscribers
        next_token: Token for retrieving next page (null if no more pages)
        count: Number of subscribers in current response
    """

    subscribers: list[Subscriber] = Field(description="List of subscribers")
    next_token: str | None = Field(default=None, description="Pagination token")
    count: int = Field(description="Number of subscribers returned")


class StatsResponse(BaseModel):
    """
    Response for statistics endpoint providing system metrics.

    Attributes:
        total_subscribers: Total number of subscribers in system
        active_count: Number of active subscribers
        inactive_count: Number of inactive subscribers
        recent_24h: Number of new subscriptions in last 24 hours
    """

    total_subscribers: int = Field(description="Total subscribers in system")
    active_count: int = Field(description="Active subscribers")
    inactive_count: int = Field(description="Inactive subscribers")
    recent_24h: int = Field(description="New subscriptions in last 24 hours")
