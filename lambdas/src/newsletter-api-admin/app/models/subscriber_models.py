"""
Domain models representing DynamoDB subscriber entities.

These models map directly to the structure of items stored in the newsletter-subscribers table.
"""

from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class Subscriber(BaseModel):
    """
    Represents a newsletter subscriber stored in the newsletter-subscribers table.

    Attributes:
        id: Unique identifier for the subscriber (UUID)
        email: Subscriber email address
        name: Subscriber name
        status: Subscription status ('active' or 'inactive')
        subscribed_at: Unix timestamp when first subscribed
        updated_at: Unix timestamp of last update
        ip_address: IP address from subscription request
        user_agent: User agent from subscription request
    """

    id: str = Field(description="Unique subscriber identifier (UUID)")
    email: EmailStr = Field(description="Subscriber email address")
    name: str = Field(description="Subscriber name")
    status: Literal["active", "inactive"] = Field(description="Subscription status")
    subscribed_at: int = Field(description="Unix timestamp when subscribed")
    updated_at: int = Field(description="Unix timestamp of last update")
    ip_address: str = Field(description="IP address from request")
    user_agent: str = Field(description="User agent from request")
