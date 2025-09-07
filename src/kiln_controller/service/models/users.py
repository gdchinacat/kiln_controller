from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = 'users'
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'email': None,
                                          'phone_number': None}

    email: Mapped[Optional[str]] = mapped_column(default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(default=None)
