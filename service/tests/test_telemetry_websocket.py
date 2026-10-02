import os
from kiln_controller.service.models import User, UserCreate, Device, DeviceCreate
from kiln_controller.service.models.db import SessionMaker

os.environ["NON_PERSISTENT"] = "TRUE"


import pytest
from typing import TypedDict, NamedTuple

from fastapi import status
from fastapi.testclient import TestClient

from kiln_controller.service.main import app


class _Auth(NamedTuple):
    username: str
    password: str


@pytest.fixture
def auth(username: str = "username", password: str = "password") -> _Auth:
    return _Auth(username, password)


@pytest.fixture
def admin_auth() -> _Auth:
    return _Auth("admin", "admin")


@pytest.fixture
def client(sessionmaker: SessionMaker) -> TestClient:
    app.state.db_sessionmaker = sessionmaker
    return TestClient(app)


class AuthenticatedUser(User):
    auth: tuple[str, str]


@pytest.fixture
def user(
    client: TestClient,
    admin_auth: auth,  # to create the user
    name: str = "name",
    username: str = "username",
    password: str = "password",
) -> AuthenticatedUser:
    create = UserCreate(name=name, username=username, password=password)
    response = client.post("/user", json=dict(create), auth=admin_auth)
    response.raise_for_status()
    json = response.json()
    json["auth"] = (username, password)
    return AuthenticatedUser.model_validate(json)


@pytest.fixture
def device(client: TestClient, user: AuthenticatedUser, name: str = "kiln") -> Device:
    create = DeviceCreate(name=name)
    response = client.post("/device", json=dict(create), auth=user.auth)
    response.raise_for_status()
    return Device.model_validate(response.json())


def test_get_device_401(client: TestClient) -> None:
    response = client.get("/device/", auth=("", ""))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_device_401(client: TestClient, user: AuthenticatedUser) -> None:
    response = client.post("/device/", json={"name": "device name"}, auth=user.auth)
    response.raise_for_status()
    device_json = response.json()
    assert device_json.get("auth_token")


def test_get_device_200(
    client: TestClient, device: Device, user: AuthenticatedUser
) -> None:
    response = client.get(f"/device/{device.id}", auth=user.auth)
    response.raise_for_status()
