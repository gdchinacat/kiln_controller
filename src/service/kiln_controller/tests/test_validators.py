# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument

from dataclasses import dataclass, field
from functools import partial
from typing import List
from unittest import TestCase

from skytap.fixtures.fixtures import default_fixture_name, fixture, pass_self

from ..common import (ValidationError, ValidationErrors, PhaseType,
                      UserValidator, ScheduleValidator, DeviceValidator)
from .helpers import SortedList


__all__ = []


# TODO - move these @dataclass fixtures into .fixtures?

@default_fixture_name('user')
@dataclass
class _User(UserValidator):
    '''User @fixture'''
    schedules: List["_Schedule"] = field(default_factory=list)
    devices: List["_Device"] = field(default_factory=list)


@default_fixture_name('device')
@dataclass
class _Device(DeviceValidator):
    '''Device @fixture'''
    user: "_User"

    def __post_init__(self):
        if self.user:
            self.user.devices.append(self)


@default_fixture_name('schedule')
@dataclass
class _Schedule(ScheduleValidator):
    '''Schedule @fixture'''
    user: _User = None
    phases: List["_Phase"] = field(
        default_factory=partial(SortedList, key=lambda phase: phase.ordinal))

    def __post_init__(self):
        if self.user is not None:
            self.user.schedules.append(self)

    @property
    def max_phase_ordinal(self):
        '''the maximum ordinal of the phases'''
        return self.phases[-1].ordinal if self.phases else 10


@default_fixture_name('phase')
@dataclass
class _Phase:
    '''Schedule @fixture'''
    ordinal: int
    phase_type: PhaseType
    temperature: int
    schedule: "_Schedule"

    def __post_init__(self):
        self.schedule.phases.append(self)

    @default_fixture_name('phase')
    @staticmethod
    def ramp(schedule, temperature=1000, ordinal=None, **kwargs):
        return _Phase(ordinal or schedule.max_phase_ordinal+10,
                      PhaseType.RAMP, temperature, schedule)

    @default_fixture_name('phase')
    @staticmethod
    def constant(schedule, temperature=1000, ordinal=None, **kwargs):
        return _Phase(ordinal or schedule.max_phase_ordinal+10,
                      PhaseType.CONSTANT, temperature, schedule)


class _ValidatorTestCase(TestCase):
    '''
    Base TestCase class for test validator test cases.

    Provides methods for encapsulating common assertion patterns.
    '''

    @pass_self
    def assertInvalid(self, resource, error: ValidationErrors, **kwargs):
        '''
        assert resource.validate() raises ValidationError with type error.
        '''
        with self.assertRaises(ValidationError) as ve:
            resource.validate_create_or_update()
        self.assertEqual(error, ve.exception.error)


class TestScheduleValidator(_ValidatorTestCase):
    """Test the schedule validator"""

    @fixture(_Schedule)
    @fixture(_Phase.constant)
    def test_first_phase_must_be_ramp(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrors.FIRST_PHASE_NOT_RAMP)

    @fixture(_Schedule)
    @fixture(_Phase.ramp, temperature=1000)
    @fixture(_Phase.constant, temperature=1500)
    def test_temperature_must_be_continous(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrors.TEMPERATURE_NOT_CONTINUOUS)

    @fixture(_Schedule)
    @fixture(_Phase.ramp)
    @fixture(_Phase.constant)
    @fixture(_Phase.constant)
    def test_no_sequential_constant_phases(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrors.SEQUENTIAL_CONSTANT_PHASES)

    @fixture(_Schedule)
    @fixture(_Phase.ramp)
    @fixture(_Phase.ramp)
    def test_no_dupliate_ramp_temperatures(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrors.DUPLICATE_RAMP_TEMPERATURES)


class TestUserValidator(_ValidatorTestCase):

    @fixture(_User)
    def test_user_delete_no_schedule_no_device(self, user):
        user.validate_delete()

    @fixture(_User)
    @fixture(_Schedule)
    def test_user_delete_with_schedule_error(self, user, **_):
        with self.assertRaises(ValidationError) as ve:
            user.validate_delete()
        self.assertEqual(ValidationErrors.USER_HAS_SCHEDULES,
                         ve.exception.error)

    @fixture(_User)
    @fixture(_Device)
    def test_user_delete_with_device_error(self, user, **_):
        with self.assertRaises(ValidationError) as ve:
            user.validate_delete()
        self.assertEqual(ValidationErrors.USER_MANAGES_DEVICES,
                         ve.exception.error)
