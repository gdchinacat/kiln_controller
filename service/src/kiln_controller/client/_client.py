from typing import TYPE_CHECKING, Self

import httpx2

from rest_client import RestClient, RootResourceList

from ._user import User
from ._device import Device
from ._schedule import Schedule, Phase


class Client(RestClient):

    if TYPE_CHECKING:
        users: RootResourceList[User]
        devices: RootResourceList[Device]
        schedules: RootResourceList[Schedule]

    def __init__(self, client: httpx2.Client):
        super().__init__(client)
        self.users = RootResourceList(User, self)
        self.devices = RootResourceList(Device, self)
        self.schedules = RootResourceList(Schedule, self)

    def expire(self) -> Self:
        self.users.expire()
        self.devices.expire()
        self.schedules.expire()
        return self
