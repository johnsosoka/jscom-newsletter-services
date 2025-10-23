"""
Request models for admin API endpoints.

These models define and validate the structure of incoming API requests.
"""

from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


class SubscriberListQueryParams(BaseModel):
    """
    Query parameters for listing subscribers.

    Attributes:
        limit: Maximum number of subscribers to return (1-100)
        next_token: Pagination token for retrieving next page
        status: Optional filter by status ('active' or 'inactive')
    """

    limit: int = Field(default=50, ge=1, le=100, description="Max subscribers per page")
    next_token: str | None = Field(default=None, description="Pagination token")
    status: Literal["active", "inactive"] | None = Field(
        default=None,
        description="Filter by subscription status"
    )


class UpdateSubscriberRequest(BaseModel):
    """
    Request body for updating a subscriber's email.

    Attributes:
        email: New email address for the subscriber
    """

    email: EmailStr = Field(description="New email address")
