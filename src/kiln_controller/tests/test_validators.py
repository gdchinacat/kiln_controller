# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument

from dataclasses import dataclass
from typing import List
from unittest import TestCase

from kiln_controller.common import PhaseType

from kiln_controller.common import ScheduleValidator, ValidationError
from skytap.fixtures.fixtures import default_fixture_name, fixture, pass_self
from kiln_controller.common.validators import ValidationErrorEnum


__all__ = []


class _Base:
    ''''base' class for validators - provides super().validate()'''
    def validate(self): ...


@dataclass
class _Phase(_Base):
    '''Simple Phase class for validator testing. Only contains the fields
    necessary for the tests in this module.'''
    ordinal: int
    phase_type: PhaseType
    temperature: int
    parent: "Schedule"


@dataclass
class _Schedule(ScheduleValidator, _Base):
    phases: List[_Phase]  # ordered by _Phase.ordinal

    def __init__(self):
        super().__init__()
        self.phases = []

    def add_phase(self, phase):
        '''add a phase to the schedule'''
        self.phases.append(phase)
        self.phases.sort(key=lambda phase: phase.ordinal)

    @property
    def _max_phase_ordinal(self):
        '''the maximum ordinal of the phases'''
        return self.phases[-1].ordinal if self.phases else 10


@default_fixture_name('schedule')
def _schedule(**_):
    return _Schedule()


@default_fixture_name('phase')
def _phase(ordinal, phase_type, temperature, schedule, **_):
    phase = _Phase(ordinal, phase_type, temperature, schedule)
    schedule.add_phase(phase)
    return phase


@default_fixture_name('phase')
def _ramp(schedule, temperature=1000, ordinal=None, **kwargs):
    return _phase(ordinal or schedule._max_phase_ordinal+10,
                  PhaseType.RAMP, temperature, schedule)


@default_fixture_name('phase')
def _constant(schedule, temperature=1000, ordinal=None, **kwargs):
    return _phase(ordinal or schedule._max_phase_ordinal+10,
                  PhaseType.CONSTANT, temperature, schedule)


class _ValidatorTestCase(TestCase):

    @pass_self
    def assertInvalid(self, resource: _Base, error: ValidationErrorEnum,
                      **kwargs):
        '''
        assert resource.validate() raises ValidationError with type error.
        '''
        with self.assertRaises(ValidationError) as ve:
            resource.validate()
        self.assertEqual(error, ve.exception.error)


class TestScheduleValidator(_ValidatorTestCase):
    """Test the schedule validator"""

    @fixture(_schedule)
    @fixture(_constant)
    def test_first_phase_must_be_ramp(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrorEnum.FIRST_PHASE_NOT_RAMP)

    @fixture(_schedule)
    @fixture(_ramp, temperature=1000)
    @fixture(_constant, temperature=1500)
    def test_temperature_must_be_continous(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrorEnum.TEMPERATURE_NOT_CONTINOUS)

    @fixture(_schedule)
    @fixture(_ramp)
    @fixture(_constant)
    @fixture(_constant)
    def test_no_sequential_constant_phases(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrorEnum.SEQUENTIAL_CONSTANT_PHASES)

    @fixture(_schedule)
    @fixture(_ramp)
    @fixture(_ramp)
    def test_no_dupliate_ramp_temperatures(self, schedule, **_):
        self.assertInvalid(schedule,
                           ValidationErrorEnum.DUPLICATE_RAMP_TEMPERATURES)
