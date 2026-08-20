"""
Client API support for validations.

Should temporarily move into client, then ultimately be derived from
openapi.json.
"""

import logging
from enum import Enum

from .enums import PhaseType

__all__ = ("ValidationError",)

logger = logging.getLogger("kiln_controller.validators")


class ValidationErrors(Enum):
    """specific validation errors"""

    GENERIC = 0  # non-specific, unspecified, or unknown errors
    FIRST_PHASE_NOT_RAMP = 1
    TEMPERATURE_NOT_CONTINUOUS = 2
    SEQUENTIAL_CONSTANT_PHASES = 3
    DUPLICATE_RAMP_TEMPERATURES = 4
    USER_HAS_SCHEDULES = 5
    USER_MANAGES_DEVICES = 6


class ValidationError(Exception):
    """Exception indicating a validation error has occurred."""

    def __init__(self, error: ValidationErrors, *args: object) -> None:
        super().__init__(*args)
        self.error = error

    @classmethod
    def from_json(
        cls: type[ValidationError], json: dict[str, str]
    ) -> ValidationError | None:
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
