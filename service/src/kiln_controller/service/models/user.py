"""
Users ORM
"""

from typing import TYPE_CHECKING

import pydantic
import sqlmodel

from ._base import ORMType
from .validators import UserValidator

__all__ = ("User", "UserCreate", "UserORM", "UserUpdate")

if TYPE_CHECKING:
    from .device import DeviceORM
    from .schedule import ScheduleORM

NAME_LENGTH = 60
USERNAME_LENGTH = 16
PASSWORD_LENGTH = 16
PHONE_LENGTH = 20
EMAIL_LENGTH = 254


class UserCreate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    password: str = pydantic.Field(max_length=PASSWORD_LENGTH)
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(default=None, max_length=PHONE_LENGTH)


class UserUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(default=None, max_length=NAME_LENGTH)
    username: str | None = pydantic.Field(default=None, max_length=USERNAME_LENGTH)
    password: str | None = pydantic.Field(default=None, max_length=PASSWORD_LENGTH)
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(default=None, max_length=PHONE_LENGTH)


class User(pydantic.BaseModel):
    id: int
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(default=None, max_length=PHONE_LENGTH)


class UserORM(UserValidator, ORMType, table=True):
    __tablename__ = "users"  # type: ignore
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    username: str = sqlmodel.Field(max_length=USERNAME_LENGTH, unique=True)
    password: str = sqlmodel.Field(max_length=PASSWORD_LENGTH)
    email: str | None = sqlmodel.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = sqlmodel.Field(default=None, max_length=PHONE_LENGTH)

    schedules: list[ScheduleORM] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    devices: list[DeviceORM] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
