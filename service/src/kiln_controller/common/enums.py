"""
Common enum definitions
"""

from enum import Enum

__all__ = ["PhaseType"]


class PhaseType(Enum):
    """the types of phases"""

    CONSTANT = "constant"
    """Hold the temperature for a specified duration"""

    RAMP = "ramp"
    """Change the temperature"""
