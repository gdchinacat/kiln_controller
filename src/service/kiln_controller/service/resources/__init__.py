"""
The Application Resources.
"""

from .device import DeviceResource, DeviceListResource
from .schedule import (ScheduleResource, ScheduleListResource, PhaseResource,
                       PhaseListResource)
from .user import UserResource, UserListResource


__all__ = ['UserResource', 'UserListResource',
           'DeviceResource', 'DeviceListResource',
           'ScheduleResource', 'ScheduleListResource',
           'PhaseResource', 'PhaseListResource',
           # 'Resource', 'ListResource',
           ]
