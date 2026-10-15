"""
This package exposes the python SDK (client) for the kiln_controller service.
"""

from rest_client import Resource
from ._auth import LoginInfo
from ._client import Client
from ._user import User
from ._device import Device
from ._schedule import Schedule, Phase, PhaseType

__all__ = [
    "Client",
    "LoginInfo",
    "User",
    "Device",
    "Schedule",
    "Phase",
    "PhaseType",
    "Resource",  # re-export base class of resources for convenience
]
