from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial, wraps
from itertools import count
from typing import Any, ClassVar, Concatenate, override

import pytest
from fixtures import kwargs

from kiln_controller.service.models import PhaseType
from kiln_controller.service.models.validators import (
    DeviceValidator,
    PhaseValidator,
    ScheduleValidator,
    UserValidator,
    ValidatableDevice,
    ValidatablePhase,
    ValidatableSchedule,
    ValidatableUser,
    ValidationError,
    ValidationErrors,
)


class SortedList[T](list[T]):
    """list subclass that sorts on insert"""

    key: Callable[[T], int]

    def __init__(self, key: Callable[[T], int]) -> None:
        super().__init__()
        self.key = key

    @staticmethod
    def _sort[**P, R](
        func: Callable[Concatenate[SortedList[T], P], R],
        reverse: bool = False,
    ) -> Callable[Concatenate[SortedList[T], P], R]:
        """decorator to sort the list after calling wrapped function"""

        @wraps(func)
        def _wrap(self: SortedList[T], *args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(self, *args, **kwargs)
            finally:
                self.sort(key=self.key)

        return _wrap

    __add__ = override(_sort(list.__add__))
    __delitem__ = override(  # pyrefly: ignore[missing-override-decorator]
        _sort(list.__delitem__)
    )
    __setitem__ = override(_sort(list.__setitem__))


@kwargs.factory
@dataclass
class _User(UserValidator, ValidatableUser):
    """User @fixture"""

    name = "name"
    schedules: list[ValidatableSchedule] = field(default_factory=list)
    devices: list[ValidatableDevice] = field(default_factory=list)


@kwargs.factory
@dataclass
class _Device(DeviceValidator, ValidatableDevice):
    """Device @fixture"""

    user: ValidatableUser

    def __post_init__(self) -> None:
        if self.user:
            self.user.devices.append(self)


@kwargs.factory
@dataclass
class _Schedule(ScheduleValidator, ValidatableSchedule):
    """Schedule @fixture"""

    user: ValidatableUser | None = None
    phases: list[ValidatablePhase] = field(
        default_factory=partial(SortedList, key=lambda phase: phase.ordinal)
    )

    def __post_init__(self) -> None:
        if self.user is not None:
            self.user.schedules.append(self)


_id = count()


@dataclass
class _Phase(PhaseValidator, ValidatablePhase):
    """Schedule @fixture"""

    name = "phase"
    ordinal: int
    phase_type: PhaseType
    temperature: int | None
    schedule: ValidatableSchedule

    _ids: ClassVar[Iterator[int]] = count()

    def __post_init__(self) -> None:
        self.schedule.phases.append(self)
        self.id = next(_id)
        self.name += f" {self.id}"

    @kwargs.factory
    @staticmethod
    def ramp(
        schedule: _Schedule,
        temperature: int = 1000,
        ordinal: int | None = None,
        **kwargs: Any,
    ) -> _Phase:
        return _Phase(
            ordinal if ordinal is not None else next(_Phase._ids),
            PhaseType.RAMP,
            temperature,
            schedule,
        )

    @kwargs.factory
    @staticmethod
    def constant(
        schedule: _Schedule,
        temperature: int = 1000,
        ordinal: int | None = None,
        **kwargs: Any,
    ) -> _Phase:
        return _Phase(
            ordinal if ordinal is not None else next(_Phase._ids),
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
def test_first_phase_must_be_ramp(schedule: _Schedule, **_: Any) -> None:
    with _assert_validation_error(ValidationErrors.FIRST_PHASE_NOT_RAMP):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp(temperature=1000)
@ kwargs["phase"] << _Phase.constant(temperature=1500)
def test_temperature_must_be_continous(schedule: _Schedule, **_: Any) -> None:
    with _assert_validation_error(ValidationErrors.TEMPERATURE_NOT_CONTINUOUS):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp()
@ kwargs["phase"] << _Phase.constant()
@ kwargs["phase"] << _Phase.constant()
def test_no_sequential_constant_phases(schedule: _Schedule, **_: Any) -> None:
    with _assert_validation_error(ValidationErrors.SEQUENTIAL_CONSTANT_PHASES):
        schedule.validate_create_or_update()


@ kwargs["schedule"] << _Schedule()
@ kwargs["phase"] << _Phase.ramp()
@ kwargs["phase"] << _Phase.ramp()
def test_no_dupliate_ramp_temperatures(schedule: _Schedule, **_: Any) -> None:
    with _assert_validation_error(
        ValidationErrors.DUPLICATE_RAMP_TEMPERATURES
    ):
        schedule.validate_create_or_update()


@ kwargs["user"] << _User()
def test_user_delete_no_schedule_no_device(user: _User) -> None:
    user.validate_delete()


@ kwargs["user"] << _User()
@ kwargs["shedule"] << _Schedule()
def test_user_delete_with_schedule_error(user: _User, **_: Any) -> None:
    with _assert_validation_error(ValidationErrors.USER_HAS_SCHEDULES):
        user.validate_delete()


@ kwargs["user"] << _User()
@ kwargs["device"] << _Device()  # type: ignore  # kwargs doesn't allow proper typing of this use-case
def test_user_delete_with_device_error(user: _User, **_: Any) -> None:
    with _assert_validation_error(ValidationErrors.USER_MANAGES_DEVICES):
        user.validate_delete()
