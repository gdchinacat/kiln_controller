"""
Device model.
"""

from typing import ClassVar

from sqlmodel import Field, Relationship

from .base import Base, MappedBase
from .user import User
from ...common import DeviceValidator

__all__ = ("DeviceBase", "Device")


class DeviceBase(Base):
    _URL_PATH: ClassVar[str] = "device"
    __public_fields__: ClassVar[set[str]] = Base.__public_fields__ | {
        "host",
        "port",
        "url",
        "user_id",
        "description",
    }

    host: str
    port: int
    url: str | None = Field(default=None)
    user_id: int = Field(foreign_key="users.id")

    description: str | None = Field(default=None)


class Device(DeviceValidator, DeviceBase, MappedBase, table=True):
    __tablename__ = "devices"
    user: User | None = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """
