"""
Device model.
"""

import secrets

import pydantic
import sqlmodel

from ._base import ResourceCreate
from .user import UserORM
from .validators import DeviceValidator

__all__ = (
    "Device",
    "DeviceCreate",
    "DeviceCreateResponse",
    "DeviceUpdate",
    "DeviceORM",
)


NAME_LENGTH = 30
AUTH_TOKEN_BYTES = 32
AUTH_TOKEN_LENGTH = 43


class DeviceCreate(ResourceCreate):
    """
    REST create model for Device.

    This is sent by the device and is intentionally minimmalistic.
    """

    name: str = pydantic.Field(max_length=NAME_LENGTH)

    def extra_attrs(self, user: UserORM) -> dict[str, str | int]:
        """provide the auth_token"""
        assert user.id is not None
        ret = super().extra_attrs(user)
        ret["auth_token"] = secrets.token_urlsafe(AUTH_TOKEN_BYTES)
        ret["user_id"] = user.id
        return ret


class DeviceCreateResponse(pydantic.BaseModel):
    id: int
    name: str
    auth_token: str = pydantic.Field(max_length=AUTH_TOKEN_LENGTH)
    user_id: int


class DeviceUpdate(pydantic.BaseModel):
    """REST update model for Device."""

    name: str | None = pydantic.Field(default=None, max_length=NAME_LENGTH)
    user_id: int | None
    description: str | None


class Device(pydantic.BaseModel):
    """Rest model for Device."""

    id: int
    name: str
    user_id: int
    description: str | None = pydantic.Field(default=None)


class DeviceORM(DeviceValidator, sqlmodel.SQLModel, table=True):
    __tablename__ = "devices"
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    auth_token: str = sqlmodel.Field(max_length=AUTH_TOKEN_LENGTH)

    """The Bearer token the device must use to authenticate."""
    description: str | None = sqlmodel.Field(default=None)

    user_id: int = sqlmodel.Field(foreign_key="users.id")

    user: UserORM | None = sqlmodel.Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """
