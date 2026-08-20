"""
The Application Resources.
"""

from .device import devices_router
from .schedule import schedules_router, phases_router
from .user import users_router

__all__ = [
    "users_router",
    "devices_router",
    "schedules_router",
    "phases_router",
]
