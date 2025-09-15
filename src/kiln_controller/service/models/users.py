'''
Users ORM
'''
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    '''
    A user of the kiln controller.
    '''
    __tablename__ = 'users'
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'username': None,
                                          'email': None,
                                          'phone_number': None}

    username: Mapped[str] = mapped_column(String(16), unique=True)
    email: Mapped[Optional[str]] = mapped_column(default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(default=None)
