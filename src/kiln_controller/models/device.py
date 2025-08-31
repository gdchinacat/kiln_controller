"""
Device model.
"""
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Device(Base):
    __tablename__ = 'devices'

    host: Mapped[str]
    port: Mapped[int]
    url: Mapped[Optional[str]]
    description: Mapped[Optional[str]] = mapped_column(default=None)
