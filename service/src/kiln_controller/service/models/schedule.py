"""
Schedule related ORMs
"""

from datetime import time

import pydantic
import sqlmodel

from ...common.enums import PhaseType
from .user import UserORM
from .validators import ScheduleValidator, PhaseValidator

__all__ = (
    "Phase",
    "PhaseCreate",
    "PhaseUpdate",
    "PhaseORM",
    "Schedule",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleORM",
)

NAME_LENGTH = 30


class ScheduleCreate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    user_id: int | None = None  # defaults to current user


class ScheduleUpdate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    user_id: int | None = None


class Schedule(ScheduleUpdate):
    id: int
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    user_id: int


class ScheduleORM(ScheduleValidator, sqlmodel.SQLModel, table=True):

    __tablename__ = "schedules"

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    user: UserORM = sqlmodel.Relationship(
        back_populates="schedules",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    user_id: int = sqlmodel.Field(foreign_key="users.id")

    phases: list["PhaseORM"] = sqlmodel.Relationship(
        back_populates="schedule",
        sa_relationship_kwargs={
            "order_by": "PhaseORM.ordinal",
            "cascade": "delete",
            "lazy": True,
        },
    )


class PhaseCreate(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=NAME_LENGTH)
    ordinal: int
    phase_type: PhaseType
    duration: time | None = None
    rate: int | None = None
    temperature: int | None = None


class PhaseUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(max_length=NAME_LENGTH)
    ordinal: int | None
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

    phase_type: PhaseType | None = None
    """the type of the phase"""

    duration: time | None = None
    """
    How long the phase lasts in minutes.

    duration is unset for type==RAMP
    """

    rate: int | None = None
    """
    The rate the temperature should be changed at in C/min.

    Unset for type==CONSTANT.
    When not set for type==RAMP indicates the temperature should change as
    rapidly as possible.
    """

    temperature: int | None = None
    """
    The temperature the phase maintains (CONSTANT) or ends with (RAMP).

    Unset to indicate ambient temperature.
    """

    schedule_id: int | None = None


class Phase(pydantic.BaseModel):
    id: int
    name: str
    ordinal: int
    phase_type: PhaseType
    duration: time | None = None
    rate: int | None = None
    temperature: int | None = None
    schedule_id: int


class PhaseORM(PhaseValidator, sqlmodel.SQLModel, table=True):
    __tablename__ = "phases"
    __table_args__ = (
        sqlmodel.UniqueConstraint("schedule_id", "name"),
        sqlmodel.UniqueConstraint("schedule_id", "ordinal"),
    )

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(default=None, max_length=NAME_LENGTH)
    ordinal: int
    phase_type: PhaseType
    duration: time | None
    rate: int | None
    temperature: int | None

    schedule_id: int = sqlmodel.Field(foreign_key="schedules.id")
    schedule: ScheduleORM = sqlmodel.Relationship(
        back_populates="phases",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """the schedule the phase is part of"""
