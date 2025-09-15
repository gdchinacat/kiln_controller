"""
Device model.
"""
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .users import User


class Device(Base):
    __tablename__ = 'devices'
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'host': None,
                                          'port': None,
                                          'url': None,
                                          'description': None}

    user: Mapped[User] = mapped_column(ForeignKey(User.id))
    '''
    The user that manages the device (not the users with access to the device).
    '''

    host: Mapped[str]
    port: Mapped[int]
    url: Mapped[Optional[str]]
    description: Mapped[Optional[str]] = mapped_column(default=None)
