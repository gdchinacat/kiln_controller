from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, primary_key, name_field
from .users import User

class Device(Base):
    __tablename__ = 'devices'
    
    id: Mapped[primary_key] = mapped_column(init=False)
    name: Mapped[name_field] 
    host: Mapped[str]
    port: Mapped[int]
    description: Mapped[Optional[str]] = mapped_column(default=None)
    #users: Mapped[List[User]] = relationship(default_factory=list)