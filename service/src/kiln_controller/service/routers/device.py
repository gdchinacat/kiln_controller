"""
Device related Flask resources
"""

from ..models import Device, DeviceORM
from .base import create_router

devices_router = create_router(Device, DeviceORM)
