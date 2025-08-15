from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, primary_key, name_field

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[primary_key] = mapped_column(init=False)
    name: Mapped[name_field]
    email: Mapped[Optional[str]] = mapped_column(default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(default=None)
    