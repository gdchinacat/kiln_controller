"""
Users ORM
"""

from typing import ClassVar, Dict, Optional, List, TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import Base
from ...common import UserValidator

if TYPE_CHECKING:
    from .schedule import Schedule
    from .device import Device


class User(UserValidator, Base, table=True):
    """
    A user of the kiln controller.
    """

    __tablename__ = "users"
    PUBLIC_FIELDS: ClassVar[Dict] = Base.PUBLIC_FIELDS | {
        "username": None,
        "email": None,
        "phone_number": None,
    }

    username: str = Field(max_length=16, unique=True)
    email: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)

    schedules: List["Schedule"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    devices: List["Device"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )