"""
The Application Resources.
"""

from .user import UserResource, UserListResource
from .device import DeviceResource, DeviceListResource
from .schedule import (ScheduleResource, ScheduleListResource, PhaseResource,
                       PhaseListResource)

__all__ = ['UserResource', 'UserListResource',
           'DeviceResource', 'DeviceListResource',
           'ScheduleResource', 'ScheduleListResource',
           'PhaseResource', 'PhaseListResource',
           # 'Resource', 'ListResource',
           ]
