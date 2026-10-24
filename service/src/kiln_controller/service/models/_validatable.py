"""
typing.Protocol definitions for resources that can be validated.

Everything the validators need to validate are defined here. This keeps the
validation decoupled from the ORMs.
"""

from enum import Enum
from typing import Protocol

__all__ = ("PhaseType",)


class ValidatorMixinBase(Protocol):
    """
    Base class for resource validators.

    This is a mixin class to add validation functionality to:
        - mapped classes in the service
        - unit test dataclasses to unit test the validator functionality.
    """

    def validate_create_or_update(self) -> None:
        """validate the state of the new or updated resource"""

    def validate_delete(self) -> None:
        """validate the resource can be deleted"""


class PhaseType(str, Enum):
    """the types of phases"""

    CONSTANT = "constant"
    RAMP = "ramp"


class ValidatableUser(Protocol):
    name: str
    schedules: list[ValidatableSchedule]
    devices: list[ValidatableDevice]


class ValidatableDevice(Protocol):
    pass


class ValidatableSchedule(ValidatorMixinBase, Protocol):
    # This is a subclass of ValidatorMixinBase so that phase validation can
    # defer to schedule validation.
    phases: list[ValidatablePhase]


class ValidatablePhase(Protocol):
    id: int
    name: str
    phase_type: PhaseType
    schedule: ValidatableSchedule
    temperature: int | None
