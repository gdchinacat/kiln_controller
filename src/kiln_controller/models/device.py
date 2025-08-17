from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, name_field
from .users import User

class Device(Base):
    __tablename__ = 'devices'
    
    name: Mapped[name_field] 
    host: Mapped[str]
    port: Mapped[int]
    url: Mapped[Optional[str]]
    description: Mapped[Optional[str]] = mapped_column(default=None)
    
    #users: Mapped[List[User]] = relationship(default_factory=list)