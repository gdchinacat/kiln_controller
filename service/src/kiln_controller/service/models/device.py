"""
Device model.
"""

from typing import Annotated, ClassVar

from sqlmodel import Field, Relationship

from .base import Base, BaseUpdate, MappedBase
from .user import UserORM
from .validators import DeviceValidator

__all__ = ("Device", "DeviceUpdate", "DeviceORM")


class DeviceUpdate(BaseUpdate):
    """the specification for what is required for a Device update (PUT)."""

    host: str | None
    port: int | None
    url: str | None
    user_id: int | None
    description: str | None


class Device(DeviceUpdate):
    _URL_PATH: ClassVar[str] = "device"

    host: str
    port: int
    user_id: int


class DeviceORM(DeviceValidator, MappedBase, Device, table=True):
    __tablename__ = "devices"
    # user: Annotated[User | None, Field(exclude=True)] = Relationship(
    user_id: int = Field(foreign_key="users.id")

    user: UserORM | None = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """
