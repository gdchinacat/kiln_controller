"""
Test the kiln_controller phase resource behavior.
"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument

from datetime import time
from functools import wraps
from itertools import count
import logging
import os

import pytest
from .fixtures import fixture

from kiln_controller.client import Phase
from .mock_service import LIVE_SERVICE
from kiln_controller.common import PhaseType, ValidationError, ValidationErrors
from .fixtures import (
    CleanupTestCase,
    mock_service_fixture,
    client_fixture,
    user_fixture,
    schedule_fixture,
)

if os.getenv("DEBUG_LOGGING", "false").upper() == "TRUE":
    logging.basicConfig(level=logging.DEBUG, force=True)


def generator_primer(func):
    """decorator to 'prime' a generator that receives values"""

    @wraps(func)
    def _generator_primer(*args, **kwargs):
        ret = func(*args, **kwargs)
        ret.send(None)
        return ret

    return _generator_primer


def _constant(**kwargs):
    """utility to create kwargs for a PhaseType.CONSTANT phase"""
    return {
        "name": None,
        "phase_type": PhaseType.CONSTANT,
        "duration": time(0, 1),
        "temperature": 1000,
    } | kwargs


def _ramp(**kwargs):
    """utility to create kwargs for a PhaseType.RAMP phase"""
    return {
        "name": None,
        "phase_type": PhaseType.RAMP,
        "rate": 100,
        "temperature": 1000,
    } | kwargs


class PhaseTest(CleanupTestCase):
    """
    Test phase resources.
    """

    @generator_primer
    def phase_generator(self, schedule):
        """
        Generator that creates a sequence of phases.

        Primarily handles common or automatic attributes of phase creation.

        gen = self.phase_sequence(schedule)
        phase1 = gen.send(_ramp())
        phase2 = gen.send(_constant())
        """
        ordinal = count(10, 10)
        kwargs = yield
        while kwargs is not None:
            _ordinal = next(ordinal)
            kwargs["name"] = kwargs.get("name", None) or f"phase{_ordinal}"
            kwargs = yield Phase(ordinal=next(ordinal), parent=schedule, **kwargs)

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_first_phase_must_be_ramp_error(self, schedule, mock_service, **_):
        """
        Verify an error occurs if the first phase is not a RAMP.

        This ensures the first step of a schedule is getting the kiln to a
        known temperature.
        """
        phases = self.phase_generator(schedule)
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                schedule.phases += phases.send(_constant())

        self.assertEqual(ValidationErrors.FIRST_PHASE_NOT_RAMP, ve.exception.error)

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_sequential_ramp_different_temperature(self, schedule, mock_service, **_):
        """
        test that sequential RAMP can't have same temperature
        """
        phases = self.phase_generator(schedule)
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                schedule.phases += phases.send(_ramp())
                schedule.phases += phases.send(_ramp())

        self.assertEqual(
            ValidationErrors.DUPLICATE_RAMP_TEMPERATURES, ve.exception.error
        )

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_sequential_constant_phases_error(self, schedule, mock_service, **_):
        """
        Since temperatures must be continuous and PhaseType.CONSTANT phases do
        not change the temperature, two sequential constant phases must have
        the same temperature and can therefore be merged. Sequential CONSTANT
        phases are not allowed.
        TODO - in order to allow schedule changes to executing schedules, if
        the current phase is not permitted to change (still undecided) the only
        way to extend it during execution will be to add a subsequent CONSTANT
        phase. Once runtime edits are implemented this may need to change.
        """
        phases = self.phase_generator(schedule)
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                schedule.phases += phases.send(_ramp())  # satisfy constraints
                schedule.phases += phases.send(_constant())
                schedule.phases += phases.send(_constant())

        self.assertEqual(
            ValidationErrors.SEQUENTIAL_CONSTANT_PHASES, ve.exception.error
        )

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_discountinous_temperature_error(self, schedule, mock_service, **_):
        """test the requirement that phases temperature must be continuous"""
        phases = self.phase_generator(schedule)
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                schedule.phases += phases.send(_ramp(temperature=500))
                schedule.phases += phases.send(_constant(temperature=1000))

        self.assertEqual(
            ValidationErrors.TEMPERATURE_NOT_CONTINUOUS, ve.exception.error
        )


if __name__ == "__main__":
    pytest.main()
