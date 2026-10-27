"""
Users ORM
"""

from typing import TYPE_CHECKING, Annotated, ClassVar

import pydantic
import sqlmodel
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ._base import ORMType
from .validators import UserValidator

__all__ = ("User", "UserCreate", "UserORM", "UserUpdate")

if TYPE_CHECKING:
    from .device import DeviceORM
    from .schedule import ScheduleORM

NAME_LENGTH = 60
USERNAME_LENGTH = 16
PASSWORD_LENGTH = 255  # to comfortably fit an argon2 hash
PHONE_LENGTH = 20
EMAIL_LENGTH = 254

PASSWORD_HASHER = PasswordHasher()


class UserCreate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    password: Annotated[str, pydantic.AfterValidator(PASSWORD_HASHER.hash)]
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(
        default=None, max_length=PHONE_LENGTH
    )


class UserUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(default=None, max_length=NAME_LENGTH)
    username: str | None = pydantic.Field(
        default=None, max_length=USERNAME_LENGTH
    )
    password: Annotated[
        str | None, pydantic.AfterValidator(PASSWORD_HASHER.hash)
    ]
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(
        default=None, max_length=PHONE_LENGTH
    )


class User(pydantic.BaseModel):
    id: int
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    username: str = pydantic.Field(max_length=USERNAME_LENGTH)
    email: str | None = pydantic.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = pydantic.Field(
        default=None, max_length=PHONE_LENGTH
    )


class UserORM(UserValidator, ORMType, table=True):
    __tablename__ = "users"  # type: ignore[bad-override]
    __table_args__: ClassVar[dict[str, bool]] = {"sqlite_autoincrement": True}

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    username: str = sqlmodel.Field(max_length=USERNAME_LENGTH, unique=True)
    password: str = sqlmodel.Field(max_length=PASSWORD_LENGTH)
    email: str | None = sqlmodel.Field(default=None, max_length=EMAIL_LENGTH)
    phone_number: str | None = sqlmodel.Field(
        default=None, max_length=PHONE_LENGTH
    )

    schedules: list[ScheduleORM] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    devices: list[DeviceORM] = sqlmodel.Relationship(
        back_populates="user",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )

    def verify_password(self, password: str) -> bool:
        try:
            return PASSWORD_HASHER.verify(self.password, password)
        except VerifyMismatchError:
            return False
