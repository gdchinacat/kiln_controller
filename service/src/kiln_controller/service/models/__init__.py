"""
The server-side data models for the kiln_controller service.
"""

from ._base import ResourceCreate, ORMType
from .db import get_sessionmaker, get_engine, SessionMaker
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
    "get_sessionmaker",
    "get_engine",
    "SessionMaker",
    "ResourceCreate",
    "FiringORM",
    "ORMType",
    *db.__all__,
    *user.__all__,
    *schedule.__all__,
    *device.__all__,
)
