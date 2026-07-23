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


class Schedule(ScheduleValidator, Base, table=True):
    """
    A schedule is a definition of how a firing should be executed.
    """

    __tablename__ = "schedules"
    __public_fields__: ClassVar[set[str]] = Base.__public_fields__ | {"user_id"}

    user_id: int = Field(foreign_key="users.id")  # todo? - serialize user as user_id=user.id
    user: User = Relationship(
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

    TODO - Clients should not be required to manage this directly as doing so
           does not fit the single-resource REST endpoints provided by the
           API. Suppose an existing set of phases with ordinals {1, 2, 3}.
           Inserting a phase between 1 and 2 requires that 3 be updated to 4,
           2 be updated to 3, then the new phase can be inserted at 2. This is
           cumbersome, requires gaps in ordinals be allowed (precluding [n-1]),
           and is not atomic, and requires unmodeled fields in requests to
           specify where to insert.
           This is being deferred to reduce server complexity by moving it to
           the client. This deferral may be revisited during implementation
           since the problem is essentially the same, the differences being
           API support for specifying where to insert vs supporting gaps. Gaps
           aren't as hard to handle as API, so it is deferred (for now).
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
    schedule: Schedule = Relationship(
        back_populates="phases",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """the schedule the phase is part of"""

    def validate_create_or_update(self) -> None:
        """Phase validation is delegated to Schedule.validate_create_or_update()."""
        self.schedule.validate_create_or_update()

    @field_serializer("phase_type")
    def serialize_phase_type(self, v: PhaseType) -> str | None:
        """Serialize PhaseType enum to its name string."""
        return v.name if v is not None else None
