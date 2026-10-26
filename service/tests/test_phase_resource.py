"""
Test the kiln_controller phase resource behavior.
"""

import logging
import os
from collections.abc import Callable, Generator
from datetime import time
from functools import wraps
from itertools import count
from typing import Any, cast

import httpx2
from fixtures import kwargs

from kiln_controller.client import Phase, PhaseType, Schedule

from ._fixtures import (
    assert_http_status_error,
    phase_fixture,
    schedule_fixture,
    user_client,
    user_fixture,
)

if os.getenv("DEBUG_LOGGING", "false").upper() == "TRUE":
    logging.basicConfig(level=logging.DEBUG, force=True)


def generator_primer[Y, S, R, **P](
    func: Callable[P, Generator[Y | None, S | None, R]],
) -> Callable[P, Generator[Y, S, R]]:
    """decorator to 'prime' a generator that receives values"""

    @wraps(func)
    def _generator_primer(
        *args: P.args, **kwargs: P.kwargs
    ) -> Generator[Y, S, R]:
        ret = func(*args, **kwargs)
        ret.send(None)
        # Remove '|None' from Y and S...they are only None for priming.
        return cast(Generator[Y, S, R], ret)

    return _generator_primer


def _constant(**kwargs: Any) -> dict[str, Any]:
    """utility to create kwargs for a PhaseType.CONSTANT phase"""
    return {
        "name": None,
        "phase_type": PhaseType.CONSTANT,
        "duration": time(0, 1),
        "temperature": 1000,
    } | kwargs


def _ramp(**kwargs: Any) -> dict[str, Any]:
    """utility to create kwargs for a PhaseType.RAMP phase"""
    return {
        "name": None,
        "phase_type": PhaseType.RAMP,
        "rate": 100,
        "temperature": 1000,
    } | kwargs


@generator_primer
def phase_generator(
    schedule: Schedule,
) -> Generator[Phase | None, dict[str, Any] | None]:
    """
    Generator that creates a sequence of phases.

    Primarily handles common or automatic attributes of phase creation.

    gen = phase_sequence(schedule)
    phase1 = gen.send(_ramp())
    phase2 = gen.send(_constant())
    """
    ordinal = count(10, 10)
    kwargs = yield None
    while kwargs is not None:
        _ordinal = next(ordinal)
        kwargs = yield Phase(
            name=kwargs.pop("name", None) or f"phase{_ordinal}",
            ordinal=_ordinal,
            parent=schedule,
            **kwargs,
        )


@kwargs.factory
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture()
def _schedule_fixture(schedule: Schedule, **_: object) -> Schedule:
    """Wrapper fixture to hide the boilerplate for creating a schedule."""
    return schedule


@ kwargs["schedule"] << _schedule_fixture()
def test_first_phase_must_be_ramp_error(schedule: Schedule, **_: Any) -> None:
    """
    Verify an error occurs if the first phase is not a RAMP.

    This ensures the first step of a schedule is getting the kiln to a
    known temperature.
    """
    phases = phase_generator(schedule)
    with assert_http_status_error(
        httpx2.codes.UNPROCESSABLE_CONTENT, "FIRST_PHASE_NOT_RAMP"
    ):
        schedule.phases += (phases.send(_constant()),)


@ kwargs["schedule"] << _schedule_fixture()
def test_sequential_ramp_duplicate_temperature(
    schedule: Schedule, **_: Any
) -> None:
    """
    test that sequential RAMP can't have same temperature
    """
    phases = phase_generator(schedule)
    with assert_http_status_error(
        httpx2.codes.UNPROCESSABLE_CONTENT, "DUPLICATE_RAMP_TEMPERATURES"
    ):
        schedule.phases += (phases.send(_ramp()), phases.send(_ramp()))


@ kwargs["schedule"] << _schedule_fixture()
def test_sequential_constant_phases_error(
    schedule: Schedule, **_: Any
) -> None:
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
    phases = phase_generator(schedule)
    with assert_http_status_error(
        httpx2.codes.UNPROCESSABLE_CONTENT, "SEQUENTIAL_CONSTANT_PHASES"
    ):
        schedule.phases += (
            phases.send(_ramp()),  # satisfy constraints
            phases.send(_constant()),
            phases.send(_constant()),
        )


@ kwargs["schedule"] << _schedule_fixture()
@ kwargs["ramp1"] << phase_fixture(  # constant must follow ramp
    name="ramp1",
    ordinal=1,
    phase_type=PhaseType.RAMP,
    temperature=1000,
    rate=100,
)
@ kwargs["constant1"] << phase_fixture(
    name="constant1",
    ordinal=2,
    phase_type=PhaseType.CONSTANT,
    temperature=1000,
    duration=time(1, 0),
)
@ kwargs["ramp_to_delete"] << phase_fixture(
    name="ramp2",
    ordinal=3,
    phase_type=PhaseType.RAMP,
    temperature=2000,
    rate=100,
)
@ kwargs["constant2"] << phase_fixture(
    name="constant2",
    ordinal=4,
    phase_type=PhaseType.CONSTANT,
    temperature=2000,
    duration=time(1, 0),
)
def test_sequential_constant_phases_ramp_delete_error(
    ramp_to_delete: Phase, **_: Any
) -> None:
    """
    Test that deleting a ramp phase between two constant phases is not
    permitted because it would create sequential constant phases.
    """
    with assert_http_status_error(
        httpx2.codes.UNPROCESSABLE_CONTENT, "SEQUENTIAL_CONSTANT_PHASES"
    ):
        ramp_to_delete.delete()


@ kwargs["schedule"] << _schedule_fixture()
def test_discountinous_temperature_error(schedule: Schedule, **_: Any) -> None:
    """test the requirement that phases temperature must be continuous"""
    phases = phase_generator(schedule)
    with assert_http_status_error(
        httpx2.codes.UNPROCESSABLE_CONTENT, "TEMPERATURE_NOT_CONTINUOUS"
    ):
        schedule.phases += (
            phases.send(_ramp(temperature=500)),
            phases.send(_constant(temperature=1000)),
        )


@ kwargs["schedule"] << _schedule_fixture()
def test_phase_order(schedule: Schedule, **_: Any) -> None:
    """
    Test that phases are ordered by ordinal rather than insert order.

    This doesn't really test that the get() orders by ordinal since there
    is a unique constraint on (schedule_id, ordinal). The index for this
    constraint is the only one for schedule, so the natural order of phases
    by schedule includes ordinal. I have manually verified that changing
    the order_by for that query to Phase.ordinal.desc() changes correctly
    changes the order and causes this test to fail.
    """

    phase2 = Phase(
        name="phase2",
        ordinal=2,
        phase_type=PhaseType.RAMP,
        temperature=950,
        parent=schedule,
    )
    phase1 = Phase(
        name="phase1",
        ordinal=1,
        phase_type=PhaseType.RAMP,
        temperature=1000,
        parent=schedule,
    )

    schedule.phases += (phase2, phase1)
    assert [phase1, phase2] == schedule.phases
