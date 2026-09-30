"""
The server-side data models for the kiln_controller service.
"""

from ._base import ResourceCreate
from .db import Session
from .user import *
from .schedule import *
from .device import *


###
# Hack FiringORM in to avovid having to come back to victoriametrics in a bit
class FiringORM:
    """stub for now...metrics needs it"""

    id = 0


DeviceORM.firing = FiringORM
### End FiringORM hack

__all__ = (
    "Session",
    "ResourceCreate",
    "FiringORM",
    *db.__all__,
    *user.__all__,
    *schedule.__all__,
    *device.__all__,
)
