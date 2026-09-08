"""
Device model.
"""

from typing import Annotated, ClassVar

from sqlmodel import Field, Relationship

from .base import Base, MappedBase
from .user import UserORM
from .validators import DeviceValidator

__all__ = ("Device", "DeviceORM")


class Device(Base):
    _URL_PATH: ClassVar[str] = "device"

    host: str
    port: int
    url: str | None = Field(default=None)
    user_id: int = Field(foreign_key="users.id")

    description: str | None = Field(default=None)


class DeviceORM(DeviceValidator, Device, MappedBase, table=True):
    __tablename__ = "devices"
    # user: Annotated[User | None, Field(exclude=True)] = Relationship(
    user: UserORM | None = Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """
