"""
CRUD domain model validations (ie can a schedule be deleted, do schedule phases
adhere to constraints). request validation is performed by pydantic based on
the model class annotations.
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING

from ...common.enums import PhaseType
from kiln_controller.common.validators import ValidationErrors, ValidationError

logger = logging.getLogger("kiln_controller.validators")
__all__ = ("ValidationError",)


if TYPE_CHECKING:
    from .device import DeviceORM
    from .schedule import ScheduleORM, PhaseORM


class ValidatorMixinBase:
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


class UserValidator(ValidatorMixinBase):
    """user validation"""

    if TYPE_CHECKING:
        name: str
        schedules: list[ScheduleORM]
        devices: list[DeviceORM]

    def validate_delete(self):
        """validate the user can be deleted"""
        super().validate_delete()
        if self.schedules:
            raise ValidationError(ValidationErrors.USER_HAS_SCHEDULES, self.name)

        if self.devices:
            raise ValidationError(ValidationErrors.USER_MANAGES_DEVICES, self.name)


class DeviceValidator(ValidatorMixinBase):
    """device validation"""


class ScheduleValidator(ValidatorMixinBase):
    """schedule validation"""

    if TYPE_CHECKING:
        phases: list[PhaseORM]

    def _validate(self) -> None:
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
        phases = self.phases
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

    def validate_create_or_update(self) -> None:
        super().validate_create_or_update()
        self._validate()

    def validate_delete(self) -> None:
        super().validate_delete()
        self._validate()


class PhaseValidator(ValidatorMixinBase):
    """phase validation"""

    if TYPE_CHECKING:
        schedule: ScheduleORM

    def validate_create_or_update(self):
        super().validate_create_or_update()
        self.schedule.validate_create_or_update()

    def validate_delete(self):
        super().validate_delete()
        self.schedule.phases.remove(self)  # type: ignore
        self.schedule.validate_delete()
