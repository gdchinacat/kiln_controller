"""
Client API support for validations.

Should temporarily move into client, then ultimately be derived from
openapi.json.
"""

import logging
from enum import Enum

__all__ = ("ValidationError",)

logger = logging.getLogger("kiln_controller.validators")


class ValidationErrors(Enum):
    """specific validation errors"""

    GENERIC = "unspecified"  # non-specific, unspecified, or unknown errors
    FIRST_PHASE_NOT_RAMP = "first phase not ramp"
    TEMPERATURE_NOT_CONTINUOUS = "temperature not continuous"
    SEQUENTIAL_CONSTANT_PHASES = "sequential constant phases"
    DUPLICATE_RAMP_TEMPERATURES = "duplicate ramp temperatures"
    USER_HAS_SCHEDULES = "user has schedules"
    USER_MANAGES_DEVICES = "user manages devices"


class ValidationError(Exception):
    """Exception indicating a validation error has occurred."""

    def __init__(self, error: ValidationErrors, input: object) -> None:
        super().__init__(input)
        self.error = error

    @property
    def input(self) -> str:
        return str(self.args[0])

    def json(self) -> dict[str, list[dict[str, str]]]:
        """get the json representation of this error"""
        return {
            "detail": [
                {
                    "type": self.error.name,
                    "msg": self.error.value,
                    "input": self.input,
                    # "input": ", ".join(
                    #    tuple(str(arg) for arg in self.args)
                    #    if self.args
                    #    else (self.error.name,)
                    # ),
                }
            ]
        }
