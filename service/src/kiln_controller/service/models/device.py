"""
Device model.
"""

from typing import ClassVar, Dict, Optional

from sqlmodel import Field, Relationship

from .base import Base
from .users import User
from ...common import DeviceValidator


class Device(DeviceValidator, Base, table=True):
    __tablename__ = "devices"
    PUBLIC_FIELDS: ClassVar[Dict] = Base.PUBLIC_FIELDS | {
        "host": None,
        "port": None,
        "url": None,
        "user_id": None,
        "description": None,
    }

    host: str
    port: int
    url: Optional[str] = Field(default=None)
    user_id: int = Field(foreign_key="users.id")
    user: Optional[User] = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """

    description: Optional[str] = Field(default=None)