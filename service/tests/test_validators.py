from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial, wraps
from typing import Concatenate, Self

import pytest

from fixtures import kwargs
from kiln_controller.service.models.validators import (
    ValidationError,
    ValidationErrors,
    PhaseType,
    UserValidator,
    ScheduleValidator,
    DeviceValidator,
    ValidatorMixinBase,
)


class SortedList[T](list):
    """list subclass that sorts on insert"""

    key: Callable[[T], int] | None = None

    def __init__(self, *args, key=None):
        super().__init__(*args)
        self.key = key

    @staticmethod
    def _sort[**P, R](
        func: Callable[Concatenate[SortedList[T], P], R],
    ) -> Callable[Concatenate[SortedList[T], P], R]:
        """decorator to sort the list after calling wrapped function"""

        @wraps(func)
        def _wrap(self: SortedList[T], *args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(self, *args, **kwargs)
            finally:
                self.sort(key=self.key)

        return _wrap

    __add__ = _sort(list.__add__)
    __delitem__ = _sort(list.__delitem__)
    __setitem__ = _sort(list.__setitem__)


@kwargs.factory
@dataclass
class _User(UserValidator):
    """User @fixture"""

    name = "name"
    schedules: list[_Schedule] = field(default_factory=list)  # type: ignore
    devices: list[_Device] = field(default_factory=list)  # type: ignore


@kwargs.factory
@dataclass
class _Device(DeviceValidator):
    """Device @fixture"""

    user: _User

    def __post_init__(self):
        if self.user:
            self.user.devices.append(self)


@kwargs.factory
@dataclass
class _Schedule(ScheduleValidator):
    """Schedule @fixture"""

    user: _User = None  # type: ignore
    phases: list[_Phase] = field(  # type: ignore
        default_factory=partial(SortedList, key=lambda phase: phase.ordinal)
    )

    def __post_init__(self):
        if self.user is not None:
            self.user.schedules.append(self)

    @property
    def max_phase_ordinal(self):
        """the maximum ordinal of the phases"""
        return self.phases[-1].ordinal if self.phases else 10


@dataclass
class _Phase:
    """Schedule @fixture"""

    name = "phase"
    ordinal: int
    phase_type: PhaseType
    temperature: int
    schedule: "_Schedule"

    def __post_init__(self):
        self.schedule.phases.append(self)
        self.id = str(self.schedule.phases)
        self.name += f" {self.id}"

    @kwargs.factory
    @staticmethod
    def ramp(schedule, temperature=1000, ordinal=None, **kwargs):
        return _Phase(
            ordinal or schedule.max_phase_ordinal + 10,
            PhaseType.RAMP,
            temperature,
            schedule,
        )

    @kwargs.factory
    @staticmethod
    def constant(schedule, temperature=1000, ordinal=None, **kwargs):
        return _Phase(
            ordinal or schedule.max_phase_ordinal + 10,
            PhaseType.CONSTANT,
            temperature,
            schedule,
        )


@contextmanager
def _assert_validation_error(
    error: ValidationErrors,
) -> Generator[pytest.ExceptionInfo[ValidationError]]:
    with pytest.raises(ValidationError) as ve:
        yield ve
    assert error == ve.value.error


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.constant()
def test_first_phase_must_be_ramp(schedule, **_):
    with _assert_validation_error(ValidationErrors.FIRST_PHASE_NOT_RAMP):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp(temperature=1000)
@ kwargs["phase"] << _Phase.constant(temperature=1500)
def test_temperature_must_be_continous(schedule, **_):
    with _assert_validation_error(ValidationErrors.TEMPERATURE_NOT_CONTINUOUS):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp()
@ kwargs["phase"] << _Phase.constant()
@ kwargs["phase"] << _Phase.constant()
def test_no_sequential_constant_phases(schedule, **_):
    with _assert_validation_error(ValidationErrors.SEQUENTIAL_CONSTANT_PHASES):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp()
@ kwargs["phase"] << _Phase.ramp()
def test_no_dupliate_ramp_temperatures(schedule, **_):
    with _assert_validation_error(ValidationErrors.DUPLICATE_RAMP_TEMPERATURES):
        schedule.validate_create_or_update()


@ kwargs["user"] << _User()
def test_user_delete_no_schedule_no_device(user):
    user.validate_delete()


@ kwargs["user"] << _User()
@ kwargs["shedule"] << _Schedule()
def test_user_delete_with_schedule_error(user, **_):
    with _assert_validation_error(ValidationErrors.USER_HAS_SCHEDULES):
        user.validate_delete()


@ kwargs["user"] << _User()
@ kwargs["device"] << _Device()  # type: ignore  # kwargs doesn't allow proper typing of this use-case
def test_user_delete_with_device_error(user, **_):
    with _assert_validation_error(ValidationErrors.USER_MANAGES_DEVICES):
        user.validate_delete()
