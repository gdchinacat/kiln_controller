"""
Users ORM
"""

from typing import Annotated, ClassVar, TYPE_CHECKING

import pydantic
import sqlmodel

from .validators import UserValidator

__all__ = ("User", "UserCreate", "UserUpdate", "UserORM")

if TYPE_CHECKING:
    from .schedule import Schedule
    from .device import Device

NAME_LENGTH = 60
USERNAME_LENGTH = 16
PASSWORD_LENGTH = 16
PHONE_LENGTH = 20
EMAIL_LENGTH = 254


class UserCreate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    password: str = pydantic.Field(max_length=PASSWORD_LENGTH)
    email: str | None = pydantic.Field(max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(max_length=PHONE_LENGTH)


class UserUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(max_length=NAME_LENGTH)
    username: str | None = pydantic.Field(max_length=USERNAME_LENGTH)
    password: str | None = pydantic.Field(max_length=PASSWORD_LENGTH)
    email: str | None = pydantic.Field(max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(max_length=PHONE_LENGTH)


class User(pydantic.BaseModel):
    id: int
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    email: str | None = pydantic.Field(max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(max_length=PHONE_LENGTH)


class UserORM(UserValidator, sqlmodel.SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    username: str = sqlmodel.Field(max_length=USERNAME_LENGTH, unique=True)
    password: str = sqlmodel.Field(max_length=PASSWORD_LENGTH)
    email: str | None = sqlmodel.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = sqlmodel.Field(default=None, max_length=PHONE_LENGTH)

    # schedules: Annotated[list["Schedule"], Field(exclude=True)] = Relationship(
    schedules: list["ScheduleORM"] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    # devices: Annotated[list["Device"], Field(exclude=True)] = Relationship(
    devices: list["DeviceORM"] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
