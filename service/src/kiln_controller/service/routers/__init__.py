"""
The Application Resources.
"""

from .auth import auth_router
from .device import devices_router
from .schedule import phases_router, schedules_router
from .user import users_router

__all__ = [
    "auth_router",
    "devices_router",
    "phases_router",
    "schedules_router",
    "users_router",
]
