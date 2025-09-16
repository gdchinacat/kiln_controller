"""
Device model.
"""
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .users import User


class Device(Base):
    __tablename__ = 'devices'
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'host': None,
                                          'port': None,
                                          'url': None,
                                          'user_id': None,
                                          'description': None}

    host: Mapped[str]
    port: Mapped[int]
    url: Mapped[Optional[str]]
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    user: Mapped[User] = relationship(viewonly=True, default=None)
    '''
    The user that manages the device (not the users with access to the device).
    '''

    description: Mapped[Optional[str]] = mapped_column(default=None)

