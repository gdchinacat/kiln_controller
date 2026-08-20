"""
API cruft. Should move into client, but ultimately be derived from openapi.json.
"""

from enum import Enum

__all__ = ["PhaseType"]


class PhaseType(Enum):
    """the types of phases"""

    CONSTANT = "constant"
    """Hold the temperature for a specified duration"""

    RAMP = "ramp"
    """Change the temperature"""
