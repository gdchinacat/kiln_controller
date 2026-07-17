"""
Common enum definitions
"""

from enum import Enum

__all__ = ["PhaseType"]


class PhaseType(Enum):
    """the types of phases"""

    CONSTANT = 1
    """Hold the temperature for a specified duration"""

    RAMP = 2
    """Change the temperature"""
