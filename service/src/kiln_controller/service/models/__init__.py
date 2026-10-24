"""
The server-side data models for the kiln_controller service.
"""

from ._base import ORMType
from .db import get_sessionmaker, get_engine, SessionMaker
from .auth import *
from .user import *
from .schedule import *
from .device import *
from ._validatable import *

from . import auth, user, schedule, device, db, _validatable


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
    "FiringORM",
    "ORMType",
    *auth.__all__,
    *db.__all__,
    *user.__all__,
    *schedule.__all__,
    *device.__all__,
    *_validatable.__all__,
)
