"""
Validation logic for model elements.

It exists in this package so that it can be used by both the server and client
mocks.
"""

from enum import Enum
from typing import List, Dict, Type, TypeVar

from .enums import PhaseType


class ValidationErrors(Enum):
    """specific validation errors"""

    GENERIC = 0  # non-specific, unspecified, or unknown errors
    FIRST_PHASE_NOT_RAMP = 1
    TEMPERATURE_NOT_CONTINUOUS = 2
    SEQUENTIAL_CONSTANT_PHASES = 3
    DUPLICATE_RAMP_TEMPERATURES = 4
    USER_HAS_SCHEDULES = 5
    USER_MANAGES_DEVICES = 6


_ValidationError = TypeVar("_ValidationError", bound="ValidationError")


class ValidationError(Exception):
    """Exception indicating a validation error has occurred."""

    def __init__(self, error: ValidationErrors, *args):
        super().__init__(*args)
        self.error = error

    @classmethod
    def from_json(
        cls: Type[_ValidationError], json: Dict[str, str]
    ) -> _ValidationError | None:
        """
        Reconstitute a ValidationError from json.

        If the json does not represent a ValidationError None is returned.
        """
        if json.get("error_type") != cls.__name__:
            return None

        error = getattr(
            ValidationErrors, json.get("validation_error"), ValidationErrors.GENERIC
        )
        args = json.get("args", ())
        return cls(error, *args)

    def json(self):
        """get the json representation of this error"""
        return {
            "error_type": type(self).__name__,
            "validation_error": self.error.name,
            "args": (
                tuple(str(arg) for arg in self.args)
                if self.args
                else (self.error.name,)
            ),
        }


class ValidatorMixinBase:
    """
    Base class for resource validators.

    This is a mixin class to add validation functionality to:
        - mapped classes in the service
        - unit test dataclasses to unit test the validator functionality.
    """

    def validate_create_or_update(self):
        """validate the state of the new or updated resource"""

    def validate_delete(self):
        """validate the resource can be deleted"""


class UserValidator(ValidatorMixinBase):
    """user validation"""

    schedules: List
    devices: List

    def validate_delete(self):
        """validate the user can be deleted"""
        super().validate_delete()
        if self.schedules:
            raise ValidationError(
                ValidationErrors.USER_HAS_SCHEDULES, "user has schedules"
            )

        if self.devices:
            raise ValidationError(
                ValidationErrors.USER_MANAGES_DEVICES, "user manages devices"
            )


class DeviceValidator(ValidatorMixinBase):
    """device validation"""


class ScheduleValidator(ValidatorMixinBase):
    """schedule validation"""

    phases: List

    def validate_create_or_update(self):
        """
        Validate the schedule is valid.

        Phases - This validation ensure there is a continuous temperature from
        start to end.
            - Sequential CONSTANT phases are not allowed since they don't
              change the temperature.
            - Sequential RAMP phases must have different temperatures.
            - First phase must be a RAMP to change from ambient to a known
              temperature.
            - A CONSTANT phase temperature must be the temperature of the
              preceeding phase.
        """
        super().validate_create_or_update()
        phases = self.phases
        if phases:
            # First phase must be a RAMP.
            if phases[0].phase_type != PhaseType.RAMP:
                raise ValidationError(
                    ValidationErrors.FIRST_PHASE_NOT_RAMP,
                    "first phase in schedule must be a ramp",
                )

            for i, phase in enumerate(phases):
                # CONSTANT phases have same temperature as preceding phase
                if (
                    i > 0
                    and phase.phase_type == PhaseType.CONSTANT
                    and phases[i - 1].temperature != phase.temperature
                ):
                    raise ValidationError(
                        ValidationErrors.TEMPERATURE_NOT_CONTINUOUS,
                        "CONSTANT phase temperature different than preceeding "
                        "phase temperature",
                    )

                # No sequential CONSTANT phases
                if (
                    i > 0
                    and phases[i - 1].phase_type == PhaseType.CONSTANT
                    and phase.phase_type == PhaseType.CONSTANT
                ):
                    raise ValidationError(
                        ValidationErrors.SEQUENTIAL_CONSTANT_PHASES,
                        "sequential CONSTANT phases not permitted",
                    )

                # Sequential RAMP must have different temperatures.
                if (
                    i > 0
                    and phases[i - 1].phase_type == PhaseType.RAMP
                    and phase.phase_type == PhaseType.RAMP
                    and phase.temperature == phases[i - 1].temperature
                ):
                    raise ValidationError(
                        ValidationErrors.DUPLICATE_RAMP_TEMPERATURES,
                        "sequential RAMP must have different temperatures",
                    )

            # Last phase must be a RAMP (disabled)
            # todo - the last phase should be a ramp to ambient temperature,
            #        but it makes building phases difficult, maybe it should
            #        be implicit? I think keeping the schedule live until back
            #        to ambient can be useful to track statistics and notify
            #        users when totally cooled down. Later...
            # if phases[-1].phase_type != PhaseType.RAMP:
            #     raise Exception("last phase in schedule must be a ramp")


class PhaseValidator(ValidatorMixinBase):
    """phase validation"""

    schedule = None

    def validate_create_or_update(self):
        super().validate_create_or_update()
        self.schedule.validate_create_or_update()
