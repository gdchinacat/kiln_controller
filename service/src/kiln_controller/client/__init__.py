"""
This package exposes the python SDK (client) for the kiln_controller service.
"""

from rest_client import Resource

from ._auth import LoginInfo
from ._client import Client
from ._device import Device
from ._schedule import Phase, PhaseType, Schedule
from ._user import User

__all__ = [
    "Client",
    "Device",
    "LoginInfo",
    "Phase",
    "PhaseType",
    "Resource",  # re-export base class of resources for convenience
    "Schedule",
    "User",
]
