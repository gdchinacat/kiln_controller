"""
Users ORM
"""

from typing import ClassVar, TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import Base
from ...common import UserValidator

__all__ = ("UserBase", "User")

if TYPE_CHECKING:
    from .schedule import Schedule
    from .device import Device


class UserBase(Base):
    """
    A user of the kiln controller.
    """

    _URL_PATH: ClassVar[str] = "user"
    __public_fields__: ClassVar[set[str]] = Base.__public_fields__ | {
        "username",
        "email",
        "phone_number",
    }

    username: str = Field(max_length=16, unique=True)
    email: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)


class User(UserValidator, UserBase, table=True):
    __tablename__ = "users"
    schedules: list["Schedule"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    devices: list["Device"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
