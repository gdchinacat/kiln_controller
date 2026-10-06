"""
The Application Resources.
"""

from .auth import auth_router
from .device import devices_router
from .schedule import schedules_router, phases_router
from .user import users_router

__all__ = [
    "auth_router",
    "users_router",
    "devices_router",
    "schedules_router",
    "phases_router",
]
