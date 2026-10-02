import asyncio
from collections.abc import Iterable, AsyncGenerator
from dataclasses import dataclass, field
import os
from queue import Queue, Empty
import time
from typing import TypedDict, NamedTuple, override, Any

from fastapi import status, FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import WebSocketDenialResponse, WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from kiln_controller.device.protocol import (
    Telemetry,
    State,
    StateEnum,
    SetTimeCommand,
    Command,
    CommandType,
)
from kiln_controller.service.main import app
from kiln_controller.service.metrics import MetricsServer
from kiln_controller.service.models import (
    User,
    UserCreate,
    Device,
    DeviceCreate,
    DeviceORM,
)
from kiln_controller.service.models.db import SessionMaker, get_engine

os.environ["NON_PERSISTENT"] = "TRUE"


class _Auth(NamedTuple):
    username: str
    password: str


@pytest.fixture
def auth(username: str = "username", password: str = "password") -> _Auth:
    return _Auth(username, password)


@pytest.fixture
def admin_auth() -> _Auth:
    return _Auth("admin", "admin")


@dataclass
class FakeMetricsServer(MetricsServer):
    received_telemetry: Queue[Telemetry] = field(default_factory=Queue[Telemetry])

    @override
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> None:
        self.received_telemetry.put(telemetry)


@pytest.fixture
def metrics_server() -> FakeMetricsServer:
    return FakeMetricsServer()


@pytest.fixture
def test_app(metrics_server: FakeMetricsServer) -> FastAPI:
    app.state.metrics_server = metrics_server
    return app


@pytest.fixture
async def engine() -> AsyncGenerator[Any, AsyncEngine]:
    app.state.db_engine = await get_engine()
    yield app.state.db_engine
    await app.state.db_engine.dispose(close=True)


@pytest.fixture
def client(
    engine: AsyncEngine, test_app: FastAPI, sessionmaker: SessionMaker
) -> TestClient:
    test_app.state.db_sessionmaker = sessionmaker
    return TestClient(app)


class AuthenticatedUser(User):
    auth: tuple[str, str]


@pytest.fixture
def user(
    client: TestClient,
    admin_auth: _Auth,  # to create the user
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


class AuthenticatedDevice(Device):
    auth_token: str


@pytest.fixture
def device(
    client: TestClient, user: AuthenticatedUser, name: str = "kiln"
) -> AuthenticatedDevice:
    create = DeviceCreate(name=name)
    response = client.post("/device", json=dict(create), auth=user.auth)
    response.raise_for_status()
    return AuthenticatedDevice.model_validate(response.json())


def test_get_device_401(client: TestClient) -> None:
    response = client.get("/device/", auth=("", ""))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_register_device(client: TestClient, user: AuthenticatedUser) -> None:
    response = client.post("/device/", json={"name": "device name"}, auth=user.auth)
    response.raise_for_status()
    device_json = response.json()
    assert device_json.get("auth_token")


def test_get_device_200(
    client: TestClient, device: Device, user: AuthenticatedUser
) -> None:
    response = client.get(f"/device/{device.id}", auth=user.auth)
    response.raise_for_status()


def test_telemetry_auth_fails(
    client: TestClient, device: Device, user: AuthenticatedUser
) -> None:
    for auth in (None, ("", ""), user.auth):  # no auth  # bad auth  # user auth
        with pytest.raises(WebSocketDenialResponse):
            with client.websocket_connect(
                f"/device/{device.id}/telemetry", auth=auth
            ) as websocket:
                assert False, "should never execute"


def more_commands(websocket: WebSocketTestSession) -> list[Command]:
    """
    return whether or not a message exists on the websocket receive.
    Usage: `assert not more_commands(websocket)`

    This works by closing the websocket and verifying it is closed without any
    bytes being read.
    """

    # TODO - why is this not actually causing a WebSocketDisconnect?
    websocket.close(reason="testing: no_message")
    commands = []
    try:
        while True:
            command_bytes = websocket.receive_bytes()
            command = CommandType.unpack(command_bytes)
            commands.append(command)
    except WebSocketDisconnect:
        return commands


@pytest.mark.timeout(1)
def test_telemetry_send_no_delta_no_set_time(
    client: TestClient,
    device: AuthenticatedDevice,
    user: AuthenticatedUser,
    metrics_server: FakeMetricsServer,
) -> None:
    """Test that a telemetry can be sent. Does not verify any commands are received."""
    with client.websocket_connect(
        f"/device/{device.id}/telemetry",
        headers={"Authorization": f"Bearer {device.auth_token}"},
    ) as websocket:
        telemetry = Telemetry(
            timestamp_ms=int(time.time() * 1000),  # time delta will be small
            uptime=1,
            state=State(StateEnum.IDLE),
            sample_count=0,
            samples=[],
        )
        # websocket passes telemetry to metrics server
        websocket.send_bytes(telemetry.pack())
        assert telemetry == metrics_server.received_telemetry.get(timeout=0.1)

        # No messages from server in response to small time delta
        assert not more_commands(websocket)


@pytest.mark.timeout(1)
def test_telemetry_large_delta_sets_time(
    client: TestClient,
    device: AuthenticatedDevice,
    user: AuthenticatedUser,
    metrics_server: FakeMetricsServer,
) -> None:
    """Test that the server sends a SetTime when delta is too great."""
    with client.websocket_connect(
        f"/device/{device.id}/telemetry",
        headers={"Authorization": f"Bearer {device.auth_token}"},
    ) as websocket:
        telemetry = Telemetry(
            timestamp_ms=0,
            uptime=1,
            state=State(StateEnum.IDLE),
            sample_count=0,
            samples=[],
        )

        # Verify telemetry is passed to metrics server.
        websocket.send_bytes(telemetry.pack())
        assert telemetry == metrics_server.received_telemetry.get(timeout=0.1)

        # Verify a SetTime command is sent.
        set_time_bytes = websocket.receive_bytes()
        set_time = SetTimeCommand.unpack(set_time_bytes)
        now = int(time.time() * 1000)
        assert (now - set_time.timestamp) == pytest.approx(0, abs=100)  # ms

        # Verify there are no more messages.
        assert not more_commands(websocket)
