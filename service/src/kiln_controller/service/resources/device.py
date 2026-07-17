"""
Device related Flask resources
"""

from ..models import Device
from .base import BaseResource, BaseListResource

__all__ = ["DeviceResource", "DeviceListResource"]


class DeviceResource(BaseResource):
    """Flask resource for Devices"""

    TYPE = Device


class DeviceListResource(BaseListResource):
    """Flask list resource for Devices"""

    TYPE = Device
