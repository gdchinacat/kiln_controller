import asyncio
from collections.abc import Iterable, AsyncGenerator, Generator
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
    Message,
    MessageType,
)
from kiln_controller.service.main import app
from kiln_controller.service.metrics import MetricsServer
from kiln_controller.service.models import (
    User,
    UserCreate,
    Device,
    DeviceCreate,
    DeviceORM,
    LoginRequest,
    SessionMaker,
    get_engine,
)
from kiln_controller.service.models.db import SessionMaker

os.environ["NON_PERSISTENT"] = "TRUE"


class _Auth(NamedTuple):
    username: str
    password: str


@dataclass
class FakeMetricsServer(MetricsServer):
    received_telemetry: Queue[Telemetry] = field(default_factory=Queue[Telemetry])

    @override
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> int:
        self.received_telemetry.put(telemetry)
        return telemetry.sample_count


@pytest.fixture
def metrics_server() -> FakeMetricsServer:
    return FakeMetricsServer()


@pytest.fixture
def test_app(metrics_server: FakeMetricsServer) -> Generator[FastAPI]:
    _metrics_server = app.state.metrics_server
    try:
        app.state.metrics_server = metrics_server
        yield app
    finally:
        app.state.metrics_server = _metrics_server


@pytest.fixture
def client(test_app: FastAPI, sessionmaker: SessionMaker) -> Generator[TestClient]:
    _sessionmaker = test_app.state.db_sessionmaker
    try:
        test_app.state.db_sessionmaker = sessionmaker
        client = TestClient(app, base_url="https://testserver")
        client.post(
            "/auth/login",
            json=LoginRequest(
                username="admin",
                password="admin",  # todo proper auth
            ).model_dump(),
        )
        yield client
    finally:
        test_app.state.db_sessionmaker = _sessionmaker


@pytest.fixture
def user(
    client: TestClient,
    name: str = "name",
    username: str = "username",
    password: str = "password",
) -> User:
    create = UserCreate(name=name, username=username, password=password)
    response = client.post("/user", json=dict(create))
    response.raise_for_status()
    json = response.json()
    return User.model_validate(json)


class AuthenticatedDevice(Device):
    auth_token: str


@pytest.fixture
def device(client: TestClient, user: User, name: str = "kiln") -> AuthenticatedDevice:
    create = DeviceCreate(name=name)
    response = client.post("/device", json=dict(create))
    response.raise_for_status()
    return AuthenticatedDevice.model_validate(response.json())


def test_get_device_401(client: TestClient) -> None:
    client.cookies.clear()
    response = client.get("/device/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_register_device(client: TestClient, user: User) -> None:
    response = client.post("/device/", json={"name": "device name"})
    response.raise_for_status()
    device_json = response.json()
    assert device_json.get("auth_token")


def test_get_device_200(client: TestClient, device: Device, user: User) -> None:
    response = client.get(f"/device/{device.id}")
    response.raise_for_status()


def test_telemetry_auth_fails(client: TestClient, device: Device, user: User) -> None:
    for auth in (
        None,  # no auth
        ("", ""),  # bad auth
        ("admin", "admin"),  # user auth
    ):
        with pytest.raises(WebSocketDenialResponse):
            with client.websocket_connect(
                f"/device/{device.id}/telemetry",
            ) as websocket:
                assert False, "should never execute"


def remaining_messages(websocket: WebSocketTestSession) -> list[Message]:
    """
    Close the websocket and return the commands remaining.

    This works by closing the websocket and verifying it is closed without any
    bytes being read.
    """

    websocket.close(reason="test: remaining_messages")
    messages = []
    try:
        while True:
            message_bytes = websocket.receive_bytes()
            message = MessageType.unpack(message_bytes)
            messages.append(message)
    except WebSocketDisconnect:
        return messages


@pytest.mark.timeout(1)
def test_telemetry_set_time_on_connect(
    client: TestClient,
    device: AuthenticatedDevice,
    user: User,
    metrics_server: FakeMetricsServer,
) -> None:
    """Test that the server sends a SetTime when the connection is established."""
    with client.websocket_connect(
        f"/device/{device.id}/telemetry",
        headers={"Authorization": f"Bearer {device.auth_token}"},
    ) as websocket:
        set_time = SetTimeCommand.unpack(websocket.receive_bytes())
        assert isinstance(set_time, SetTimeCommand)

        now = int(time.time() * 1000)
        assert (now - set_time.timestamp) == pytest.approx(0, abs=100)  # ms


@pytest.mark.timeout(1)
def test_telemetry_send_no_delta_no_set_time(
    client: TestClient,
    device: AuthenticatedDevice,
    user: User,
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
        assert SetTimeCommand.unpack(websocket.receive_bytes())  # on connect

        # websocket passes telemetry to metrics server
        websocket.send_bytes(telemetry.pack())
        assert telemetry == metrics_server.received_telemetry.get(timeout=0.1)

        # No messages from server in response to small time delta
        assert not remaining_messages(websocket)


@pytest.mark.timeout(1)
def test_telemetry_large_delta_sets_time(
    client: TestClient,
    device: AuthenticatedDevice,
    user: User,
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

        assert SetTimeCommand.unpack(websocket.receive_bytes())  # on connect

        # Verify telemetry is passed to metrics server.
        websocket.send_bytes(telemetry.pack())
        assert telemetry == metrics_server.received_telemetry.get(timeout=0.1)

        # Verify a SetTime command is sent.
        set_time_bytes = websocket.receive_bytes()
        set_time = SetTimeCommand.unpack(set_time_bytes)
        now = int(time.time() * 1000)
        assert (now - set_time.timestamp) == pytest.approx(0, abs=100)  # ms

        # Verify there are no more messages.
        assert not remaining_messages(websocket)
