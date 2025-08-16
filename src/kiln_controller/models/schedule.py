from typing import List, Optional
from datetime import time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base, name_field

class Phase(Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "phases"
    
    name: Mapped[name_field]
    type: Mapped[str]
    duration: Mapped[Optional[time]]
    rate:  Mapped[Optional[int]] # degrees C per minute
    schedule_id: Mapped[Optional[int]] = mapped_column(ForeignKey('schedules.id'))
    
    #schedule = relationship("Schedule", cascade="all")
    
class Schedule(Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "schedules"
    
    name: Mapped[name_field]
    
    #phases: Mapped[List[Phase]] = relationship(back_populates="schedule",
    #                                           default_factory=list)

    