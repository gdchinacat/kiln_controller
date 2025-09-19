'''
Schedule related ORMs
'''

from datetime import time
from typing import List, Optional

from sqlalchemy import ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...common import PhaseType, ScheduleValidator, PhaseValidator
from .base import Base
from .users import User


__all__ = ['Phase', 'Schedule']


class Schedule(ScheduleValidator, Base):  # pylint: disable=too-few-public-methods
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "schedules"
    PUBLIC_FIELDS = Base.PUBLIC_FIELDS | {'user_id': None}

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    user: Mapped[User] = relationship(User,
                                      back_populates='schedules',
                                      viewonly=True,
                                      default=None,
                                      lazy=True)

    phases: Mapped[List["Phase"]] = relationship(default_factory=list,
                                                 order_by="Phase.ordinal",
                                                 cascade="delete",
                                                 lazy=True)


class Phase(PhaseValidator, Base):
    """
    A schedule is a definition of how a firing should be executed.
    """
    __tablename__ = "phases"
    __table_args__ = (
        UniqueConstraint('schedule_id', 'name'),
        UniqueConstraint('schedule_id', 'ordinal'),
    )

    PUBLIC_FIELDS = (Base.PUBLIC_FIELDS |
                     {'phase_type': lambda x: x.name if x else None,
                      'duration': lambda x: x.isoformat() if x else None,
                      'rate': None,
                      'temperature': None,
                      'ordinal': None,
                      'schedule_id': None,
                      })

    ordinal: Mapped[int]
    '''
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
    '''

    phase_type: Mapped[PhaseType] = mapped_column(Enum(PhaseType))
    '''the type of the phase'''

    duration: Mapped[Optional[time]]
    '''
    How long the phase lasts in minutes.

    duration is unset for type==RAMP
    '''

    rate:  Mapped[Optional[int]]
    '''
    The rate the temperature should be changed at in C/min.

    Unset for type==CONSTANT.
    When not set for type==RAMP indicates the temperature should change as
    rapidly as possible.
    '''

    temperature: Mapped[Optional[int]]
    '''
    The temperature the phase maintains (CONSTANT) or ends with (RAMP).

    Unset to indicate ambient temperature.
    '''

    schedule_id: Mapped[int] = mapped_column(ForeignKey(Schedule.id))
    schedule: Mapped[Schedule] = relationship(back_populates='phases',
                                              viewonly=True, default=None,
                                              lazy=True)
    '''the schedule the phase is part of'''

    def validate(self):
        '''Phase validation is delegated to Schedule.validate().'''
        return self.schedule.validate()
