"""
CRUD domain model validations (ie can a schedule be deleted, do schedule phases
adhere to constraints). request validation is performed by pydantic based on
the model class annotations.
"""

from enum import Enum
import logging
from typing import Protocol

from ...common.validators import ValidationErrors, ValidationError
from ._validatable import (
    PhaseType,
    ValidatableUser,
    ValidatableDevice,
    ValidatableSchedule,
    ValidatablePhase,
)


class UserValidator:
    """user validation"""

    def validate_delete(self: ValidatableUser) -> None:
        """validate the user can be deleted"""
        if self.schedules:
            raise ValidationError(ValidationErrors.USER_HAS_SCHEDULES, self.name)

        if self.devices:
            raise ValidationError(ValidationErrors.USER_MANAGES_DEVICES, self.name)


class DeviceValidator:
    """device validation"""


class ScheduleValidator:
    """schedule validation"""

    @staticmethod
    def _validate(schedule: ValidatableSchedule) -> None:
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
        phases = schedule.phases
        if phases:
            # First phase must be a RAMP.
            if phases[0].phase_type != PhaseType.RAMP:
                raise ValidationError(
                    ValidationErrors.FIRST_PHASE_NOT_RAMP,
                    f"{phases[0].name}({phases[0].id})",
                )

            for i, phase in enumerate(phases):
                # No sequential CONSTANT phases
                if (
                    i > 0
                    and phases[i - 1].phase_type == PhaseType.CONSTANT
                    and phase.phase_type == PhaseType.CONSTANT
                ):
                    raise ValidationError(
                        ValidationErrors.SEQUENTIAL_CONSTANT_PHASES,
                        f"{phases[i].name}({phases[i].id})",
                    )

                # CONSTANT phases have same temperature as preceding phase
                if (
                    i > 0
                    and phase.phase_type == PhaseType.CONSTANT
                    and phases[i - 1].temperature != phase.temperature
                ):
                    raise ValidationError(
                        ValidationErrors.TEMPERATURE_NOT_CONTINUOUS,
                        f"{phases[i].name}({phases[i].id})",
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
                        f"{phases[i].name}({phases[i].id})",
                    )

            # Last phase must be a RAMP (disabled)
            # todo - the last phase should be a ramp to ambient temperature,
            #        but it makes building phases difficult, maybe it should
            #        be implicit? I think keeping the schedule live until back
            #        to ambient can be useful to track statistics and notify
            #        users when totally cooled down. Later...
            # if phases[-1].phase_type != PhaseType.RAMP:
            #     raise Exception("last phase in schedule must be a ramp")

    def validate_create_or_update(self: ValidatableSchedule) -> None:
        ScheduleValidator._validate(self)

    def validate_delete(self: ValidatableSchedule) -> None:
        ScheduleValidator._validate(self)


class PhaseValidator:
    """phase validation"""

    def validate_create_or_update(self: ValidatablePhase) -> None:
        self.schedule.validate_create_or_update()

    def validate_delete(self: ValidatablePhase) -> None:
        self.schedule.phases.remove(self)
        self.schedule.validate_delete()
