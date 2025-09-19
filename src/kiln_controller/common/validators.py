'''
Validation logic for model elements.

It exists in this package so that it can be used by both the server and client
mocks.
'''
from enum import Enum
from typing import List

from .enums import PhaseType


class ValidationErrorEnum(Enum):
    '''specific validation errors'''

    FIRST_PHASE_NOT_RAMP = 1
    TEMPERATURE_NOT_CONTINOUS = 2
    SEQUENTIAL_CONSTANT_PHASES = 3
    DUPLICATE_RAMP_TEMPERATURES = 4


class ValidationError(Exception):
    '''Exception indicating a validation error has occurred.'''
    def __init__(self, error: ValidationErrorEnum, *args):
        super().__init__(*args)
        self.error = error


class ScheduleValidator:

    phases: List

    def validate(self):
        '''
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
        '''
        super().validate()  # pylint: disable=no-member

        # Validate the phases.
        phases = self.phases
        if phases:
            # First phase must be a RAMP.
            if phases[0].phase_type != PhaseType.RAMP:
                raise ValidationError(ValidationErrorEnum.FIRST_PHASE_NOT_RAMP,
                                      "first phase in schedule must be a ramp")

            for i, phase in enumerate(phases):
                # CONSTANT phases have same temperature as preceding phase
                if (i > 0 and
                        phase.phase_type == PhaseType.CONSTANT and
                        phases[i-1].temperature != phase.temperature):
                    raise ValidationError(
                        ValidationErrorEnum.TEMPERATURE_NOT_CONTINOUS,
                        "CONSTANT phase temperature different than preceeding "
                        "phase temperature")

                # No sequential CONSTANT phases
                if (i > 0 and
                        phases[i-1].phase_type == PhaseType.CONSTANT and
                        phase.phase_type == PhaseType.CONSTANT):
                    raise ValidationError(
                        ValidationErrorEnum.SEQUENTIAL_CONSTANT_PHASES,
                        "sequential CONSTANT phases not permitted")

                # Sequential RAMP must have different temperatures.
                if (i > 0 and
                        phases[i-1].phase_type == PhaseType.RAMP and
                        phase.phase_type == PhaseType.RAMP and 
                        phase.temperature == phases[i-1].temperature):
                    raise ValidationError(
                        ValidationErrorEnum.DUPLICATE_RAMP_TEMPERATURES,
                        "sequential RAMP must have different temperatures")

            # Last phase must be a RAMP (disabled)
            # todo - the last phase should be a ramp to ambient temperature,
            #        but it makes building phases difficult, maybe it should
            #        be implicit? I think keeping the schedule live until back
            #        to ambient can be useful to track statistics and notify
            #        users when totally cooled down. Later...
            # if phases[-1].phase_type != PhaseType.RAMP:
            #     raise Exception("last phase in schedule must be a ramp")
