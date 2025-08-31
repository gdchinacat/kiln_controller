from datetime import time
from typing import List, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Phase(Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "phases"

    type: Mapped[str]
    duration: Mapped[Optional[time]]
    rate:  Mapped[Optional[int]]  # degrees C per minute

    schedule_id: Mapped[int] = mapped_column(ForeignKey('schedules.id'))
    schedule: Mapped["Schedule"] = relationship()  # back_populates="phases")

    def __setattr__(self, attr, value):
        if attr == "schedule":
            value = Schedule(**value)
            print(f"using {value=}")
        super().__setattr__(attr, value)


class Schedule(Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "schedules"

    phases: Mapped[List["Phase"]] = relationship(back_populates="schedule")
