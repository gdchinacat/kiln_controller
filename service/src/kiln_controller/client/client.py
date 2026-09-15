"""
A requests-based client for interacting with the REST server.

Exposes domain-specific resources (User, Device, Schedule, Phase) and high-level
client wrapper interfaces.
"""

import datetime
from dataclasses import dataclass, field
from typing import Dict, Callable

from ..common.enums import PhaseType
from ._base import (
    BaseRestClient,
    DataclassBase,
    Resource,
    ResourceList,
    ResourceListDescriptor,
)


@dataclass
class UserBase(DataclassBase):
    username: str
    password: str | None = None
    email: str | None = None
    phone_number: str | None = None


@dataclass
class DeviceBase(DataclassBase):
    user_id: int
    host: str
    port: int
    url: str = "/"
    description: str | None = None


@dataclass
class PhaseBase(DataclassBase):
    ordinal: int
    phase_type: PhaseType
    duration: datetime.time | None = None
    rate: int | None = None
    temperature: int | None = None
    schedule_id: int | None = None

    def asdict(self) -> Dict:
        ret = super().asdict()
        ret["phase_type"] = self.phase_type.value
        ret["duration"] = str(self.duration) if self.duration else None
        return ret

    def __post_init__(self):
        """Convert fields to proper types upon initialization."""
        if self.schedule_id is not None:
            self.schedule_id = int(self.schedule_id)
        if isinstance(self.phase_type, str):
            self.phase_type = PhaseType(self.phase_type)
        if isinstance(self.duration, str):
            self.duration = datetime.datetime.strptime(self.duration, "%H:%M:%S").time()


@dataclass
class ScheduleBase(DataclassBase):
    user_id: int
    phases: ResourceList["Phase"] = field(repr=False)
    phases: ResourceList["Phase"] = ResourceListDescriptor(PhaseBase)

    def asdict(self):
        return {"id": self.id, "name": self.name, "user_id": self.user_id}


class _Client(BaseRestClient):
    """
    Internal client responsible for binding resources dynamically to REST paths.
    """

    resource_class_map = {}

    users: ResourceList["User"]
    devices: ResourceList["Device"]
    schedules: ResourceList["Schedule"]

    # Expose lists of top-level resources dynamically
    for name, base in (
        ("user", UserBase),
        ("device", DeviceBase),
        ("schedule", ScheduleBase),
        ("phase", PhaseBase),
    ):
        url = f"/{name}"
        resource = Resource.new(base, url)
        base.concrete_type = resource
        resource_class_map[name.capitalize()] = resource

        locals()[f"{name}s"] = property(ResourceList.factory(resource, url))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = self


# Type-hint placeholders exposed at module level
User: Callable = lambda *_, **__: None
Device: Callable = lambda *_, **__: None
Schedule: Callable = lambda *_, **__: None
Phase: Callable = lambda *_, **__: None

# Bind dynamically created resource classes to module level exports
_name, _cls = None, None
for _name, _cls in _Client.resource_class_map.items():
    locals()[_name] = _cls
del _name, _cls


class Client:
    """
    The main client interface for the application.

    Provides high-level access to top-level resource collections.
    """

    users: ResourceList
    devices: ResourceList
    schedules: ResourceList

    def __init__(self, *args, **kwargs):
        self._client = _Client(*args, **kwargs)

        self.users = self._client.users
        self.devices = self._client.devices
        self.schedules = self._client.schedules

    def expire(self) -> "Client":
        self.users.expire()
        self.devices.expire()
        self.schedules.expire()
        return self
