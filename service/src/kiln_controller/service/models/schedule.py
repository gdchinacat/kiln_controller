"""
Schedule related ORMs
"""

from datetime import time
from typing import ClassVar

from sqlalchemy import UniqueConstraint, Enum as SAEnum
from sqlmodel import Field, Relationship, Column
from pydantic import field_serializer

from ...common import PhaseType, ScheduleValidator, PhaseValidator
from .base import Base
from .user import User

__all__ = ["Phase", "Schedule"]


class Schedule(ScheduleValidator, Base, table=True):  # pylint: disable=too-few-public-methods
    """
    A schedule is a definition of how a firing should be executed.
    """

    __tablename__ = "schedules"
    __public_fields__: ClassVar[set[str]] = Base.__public_fields__ | {"user_id"}

    user_id: int = Field(foreign_key="users.id")
    user: User | None = Relationship(
        back_populates="schedules",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )

    phases: list["Phase"] = Relationship(
        back_populates="schedule",
        sa_relationship_kwargs={
            "order_by": "Phase.ordinal",
            "cascade": "delete",
            "lazy": True,
        },
    )


class Phase(PhaseValidator, Base, table=True):
    """
    A phase in a firing schedule.
    """

    __tablename__ = "phases"
    __table_args__ = (
        UniqueConstraint("schedule_id", "name"),
        UniqueConstraint("schedule_id", "ordinal"),
    )

    __public_fields__: ClassVar[set[str]] = Base.__public_fields__ | {
        "phase_type",
        "duration",
        "rate",
        "temperature",
        "ordinal",
        "schedule_id",
    }

    ordinal: int
    """
    The ordinal indicates the order of phases within a schedule.

    For the time being, the recommendation is that clients create gaps in
    ordinals between phases to allow subsequent insertions. Since it is not
    expected have more than 10 or so phases per schedule gaps of 10 should be
    sufficient (so BASIC).
    """

    phase_type: PhaseType = Field(sa_column=Column(SAEnum(PhaseType), nullable=False))
    """the type of the phase"""

    duration: time | None = Field(default=None)
    """
    How long the phase lasts in minutes.

    duration is unset for type==RAMP
    """

    rate: int | None = Field(default=None)
    """
    The rate the temperature should be changed at in C/min.

    Unset for type==CONSTANT.
    When not set for type==RAMP indicates the temperature should change as
    rapidly as possible.
    """

    temperature: int | None = Field(default=None)
    """
    The temperature the phase maintains (CONSTANT) or ends with (RAMP).

    Unset to indicate ambient temperature.
    """

    schedule_id: int = Field(foreign_key="schedules.id")
    schedule: Schedule | None = Relationship(
        back_populates="phases",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """the schedule the phase is part of"""

    def validate_create_or_update(self):
        """Phase validation is delegated to Schedule.validate_create_or_update()."""
        return self.schedule.validate_create_or_update()

    @field_serializer("phase_type")
    def serialize_phase_type(self, v: PhaseType) -> str | None:
        """Serialize PhaseType enum to its name string."""
        return v.name if v is not None else None
