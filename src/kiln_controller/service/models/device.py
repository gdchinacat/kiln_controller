"""
Device model.
"""
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Device(Base):
    __tablename__ = 'devices'
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'host': None,
                                          'port': None,
                                          'url': None,
                                          'description': None}

    host: Mapped[str]
    port: Mapped[int]
    url: Mapped[Optional[str]]
    description: Mapped[Optional[str]] = mapped_column(default=None)
