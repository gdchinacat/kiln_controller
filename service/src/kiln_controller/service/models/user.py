"""
Users ORM
"""

from typing import Annotated, ClassVar, TYPE_CHECKING

from sqlmodel import Field, Relationship

from .base import Base, MappedBase
from .validators import UserValidator

__all__ = ("User", "UserORM")

if TYPE_CHECKING:
    from .schedule import Schedule
    from .device import Device


class User(Base):
    """
    A user of the kiln controller.
    """

    _URL_PATH: ClassVar[str] = "user"

    username: str = Field(max_length=16, unique=True)
    email: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)


class UserORM(UserValidator, User, MappedBase, table=True):
    __tablename__ = "users"
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
