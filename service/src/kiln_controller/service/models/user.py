"""
Users ORM
"""

from typing import Annotated, ClassVar, TYPE_CHECKING

import pydantic
from sqlmodel import Field, Relationship

from .base import Base, BaseUpdate, MappedBase
from .validators import UserValidator

__all__ = ("User", "UserCreate", "UserUpdate", "UserORM")

if TYPE_CHECKING:
    from .schedule import Schedule
    from .device import Device

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 16


class UserUpdate(BaseUpdate):
    username: str | None = pydantic.Field(max_length=MAX_USERNAME_LENGTH)
    password: str | None = pydantic.Field(max_length=MAX_PASSWORD_LENGTH)
    email: str | None
    phone_number: str | None


class User(UserUpdate):
    """
    A user of the kiln controller.
    """

    _URL_PATH: ClassVar[str] = "user"

    username: str
    email: str | None
    phone_number: str | None


class UserCreate(User):
    password: str = pydantic.Field(max_length=16)


class UserORM(UserValidator, MappedBase, UserCreate, table=True):
    __tablename__ = "users"

    username: str = Field(max_length=16, unique=True)
    password: str = Field(max_length=16)
    email: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)

    # schedules: Annotated[list["Schedule"], Field(exclude=True)] = Relationship(
    schedules: list["ScheduleORM"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    # devices: Annotated[list["Device"], Field(exclude=True)] = Relationship(
    devices: list["DeviceORM"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
