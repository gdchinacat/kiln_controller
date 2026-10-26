"""
The server-side data models for the kiln_controller service.
"""

from . import _validatable, auth, db, device, schedule, user
from ._base import ORMType
from ._validatable import *
from .auth import *
from .db import SessionMaker, get_engine, get_sessionmaker
from .device import *
from .schedule import *
from .user import *


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
