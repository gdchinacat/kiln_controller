"""
Users ORM
"""

from typing import Optional, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from ...common import UserValidator


class User(UserValidator, Base):
    """
    A user of the kiln controller.
    """

    __tablename__ = "users"
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {
        "username": None,
        "email": None,
        "phone_number": None,
    }

    username: Mapped[str] = mapped_column(String(16), unique=True)
    email: Mapped[Optional[str]] = mapped_column(default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(default=None)

    schedules: Mapped[List["Schedule"]] = relationship(
        default_factory=list, viewonly=True, lazy=True
    )
    devices: Mapped[List["Device"]] = relationship(
        default_factory=list, viewonly=True, lazy=True
    )
