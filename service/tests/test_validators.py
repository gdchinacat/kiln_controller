from dataclasses import dataclass, field
from functools import partial
from typing import List
from unittest import TestCase

import pytest

from kiln_controller.service.models.validators import (
    ValidationError,
    ValidationErrors,
    PhaseType,
    UserValidator,
    ScheduleValidator,
    DeviceValidator,
)
from .helpers import SortedList
from fixtures import kwargs

__all__ = []


@kwargs.factory
@dataclass
class _User(UserValidator):
    """User @fixture"""

    schedules: List["_Schedule"] = field(default_factory=list)
    devices: List["_Device"] = field(default_factory=list)


@kwargs.factory
@dataclass
class _Device(DeviceValidator):
    """Device @fixture"""

    user: "_User"

    def __post_init__(self):
        if self.user:
            self.user.devices.append(self)


@kwargs.factory
@dataclass
class _Schedule(ScheduleValidator):
    """Schedule @fixture"""

    user: _User = None
    phases: List["_Phase"] = field(
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

    ordinal: int
    phase_type: PhaseType
    temperature: int
    schedule: "_Schedule"

    def __post_init__(self):
        self.schedule.phases.append(self)

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


class _ValidatorTestCase(TestCase):
    """
    Base TestCase class for test validator test cases.

    Provides methods for encapsulating common assertion patterns.
    """

    def assertInvalid(self, resource, error: ValidationErrors, **kwargs):
        """
        assert resource.validate() raises ValidationError with type error.
        """
        with self.assertRaises(ValidationError) as ve:
            resource.validate_create_or_update()
        self.assertEqual(error, ve.exception.error)


class TestScheduleValidator(_ValidatorTestCase):
    """Test the schedule validator"""

    @ kwargs["schedule"] << _Schedule()
    @ kwargs["phase"] << _Phase.constant()
    def test_first_phase_must_be_ramp(self, schedule, **_):
        self.assertInvalid(schedule, ValidationErrors.FIRST_PHASE_NOT_RAMP)

    @ kwargs["schedule"] << _Schedule()
    @ kwargs["phase"] << _Phase.ramp(temperature=1000)
    @ kwargs["phase"] << _Phase.constant(temperature=1500)
    def test_temperature_must_be_continous(self, schedule, **_):
        self.assertInvalid(schedule, ValidationErrors.TEMPERATURE_NOT_CONTINUOUS)

    @ kwargs["schedule"] << _Schedule()
    @ kwargs["phase"] << _Phase.ramp()
    @ kwargs["phase"] << _Phase.constant()
    @ kwargs["phase"] << _Phase.constant()
    def test_no_sequential_constant_phases(self, schedule, **_):
        self.assertInvalid(schedule, ValidationErrors.SEQUENTIAL_CONSTANT_PHASES)

    @ kwargs["schedule"] << _Schedule()
    @ kwargs["phase"] << _Phase.ramp()
    @ kwargs["phase"] << _Phase.ramp()
    def test_no_dupliate_ramp_temperatures(self, schedule, **_):
        self.assertInvalid(schedule, ValidationErrors.DUPLICATE_RAMP_TEMPERATURES)


class TestUserValidator(_ValidatorTestCase):

    @ kwargs["user"] << _User()
    def test_user_delete_no_schedule_no_device(self, user):
        user.validate_delete()

    @ kwargs["user"] << _User()
    @ kwargs["shedule"] << _Schedule()
    def test_user_delete_with_schedule_error(self, user, **_):
        with self.assertRaises(ValidationError) as ve:
            user.validate_delete()
        self.assertEqual(ValidationErrors.USER_HAS_SCHEDULES, ve.exception.error)

    @ kwargs["user"] << _User()
    @ kwargs["device"] << _Device()
    def test_user_delete_with_device_error(self, user, **_):
        with self.assertRaises(ValidationError) as ve:
            user.validate_delete()
        self.assertEqual(ValidationErrors.USER_MANAGES_DEVICES, ve.exception.error)
