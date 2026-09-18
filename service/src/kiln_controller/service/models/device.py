"""
Device model.
"""

from typing import Annotated, ClassVar

import pydantic
import sqlmodel

from .user import UserORM
from .validators import DeviceValidator

__all__ = ("Device", "DeviceUpdate", "DeviceORM")


NAME_LENGTH = 30


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
    description: str | None = sqlmodel.Field(default=None)

    user_id: int = sqlmodel.Field(foreign_key="users.id")

    user: UserORM | None = sqlmodel.Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """
