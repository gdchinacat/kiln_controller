'''
Schedule related ORMs
'''

from datetime import time
from typing import List, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

__all__ = ['Phase', 'Schedule']


class Phase(Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "phases"
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'type': None,
                                          'duration': str,
                                          'rate': None,
                                          'schedule_id': None,
                                          }

    type: Mapped[str]
    duration: Mapped[Optional[time]]
    rate:  Mapped[Optional[int]]  # degrees C per minute

    schedule_id: Mapped[int] = mapped_column(ForeignKey('schedules.id'))

    def __setattr__(self, attr, value):
        if attr == "schedule":
            value = Schedule(**value)
            print(f"using {value=}")
        super().__setattr__(attr, value)


class Schedule(Base):  # pylint: disable=too-few-public-methods
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "schedules"
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {}

    phases: Mapped[List["Phase"]] = relationship(default_factory=list)
