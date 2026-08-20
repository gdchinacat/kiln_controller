"""
Device related Flask resources
"""

from ..models import DeviceBase, Device
from .base import create_router

devices_router = create_router(DeviceBase, Device)
