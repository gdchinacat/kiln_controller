from collections.abc import Callable
from typing import TYPE_CHECKING, Self

import httpx2

from rest_client import RestClient, RootResourceList

from ._auth import LoginInfo
from ._device import Device
from ._schedule import Schedule
from ._user import User


class Client(RestClient):

    if TYPE_CHECKING:
        users: RootResourceList[User]
        devices: RootResourceList[Device]
        schedules: RootResourceList[Schedule]

    def __init__(self, client: httpx2.Client) -> None:
        super().__init__(client)
        self.users = RootResourceList(User, self)
        self.devices = RootResourceList(Device, self)
        self.schedules = RootResourceList(Schedule, self)

    def expire(self) -> Self:
        self.users.expire()
        self.devices.expire()
        self.schedules.expire()
        return self

    def login(self, username: str, password: str) -> User:
        response = self._http_client.post(
            "/auth/login",
            json=LoginInfo(
                username=username,
                password=password,
            ).model_dump(),
        ).raise_for_status()
        return User.model_validate(response.json())

    def logout(
        self, method: Callable[..., httpx2.Response] = httpx2.Client.post
    ) -> None:
        assert method in (httpx2.Client.get, httpx2.Client.post)
        method(
            self._http_client,
            "/auth/logout",
        ).raise_for_status()
