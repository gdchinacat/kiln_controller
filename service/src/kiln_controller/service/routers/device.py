"""
Device related Flask resources
"""

from asyncio import Queue, get_running_loop, TaskGroup
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
import logging
import time
from typing import Any

from fastapi import (
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import selectinload

from ...device.protocol import Telemetry, SetTimeCommand, Command
from ..dependencies import sessionmaker, metrics_server
from ..metrics import MetricsServer
from ..models import (
    Device,
    DeviceCreate,
    DeviceCreateResponse,
    DeviceUpdate,
    DeviceORM,
    User,
    SessionMaker,
)
from .base import create_router, authenticate_user

devices_router = create_router(
    "device",
    Device,
    DeviceORM,
    resource_update_type=DeviceUpdate,
    resource_create_type=DeviceCreate,
    resource_create_response_type=DeviceCreateResponse,
)


logger = logging.getLogger("kiln_controller.device")


async def _authenticate_device_websocket(
    device_id: int,
    websocket: WebSocket,
    sessionmaker: SessionMaker = sessionmaker,
) -> DeviceORM:
    auth_header = websocket.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ")[1]

        async with sessionmaker(expire_on_commit=False) as session:
            device_orm = await session.get(
                DeviceORM, device_id, options=[selectinload(DeviceORM.user)]
            )
            if not device_orm:
                # todo - is it OK to expose this as 404 without auth passing to let
                #        the device know it needs to re-register?
                # todo - no test failed when this 401 was changed to 404, need test
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            if device_orm.auth_token == auth_token:
                return device_orm
    raise HTTPException(
        # todo - don't send json auth errors
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


type Receiver = Callable[[], Coroutine[Any, Any, bytes]]
type Sender = Callable[[bytes], Coroutine[Any, Any, None]]


@dataclass
class _TelemetryIO:
    metrics_server: MetricsServer
    receive_bytes: Receiver
    send_bytes: Sender
    authenticator: Callable[[], Coroutine[Any, Any, DeviceORM]]

    queue: Queue[Command] = field(default_factory=Queue, init=False)

    # todo - send a time sync on connection

    # todo - change from request/response model to full bidirectional mode
    # todo - create a task for sending commands
    # todo? - create a metric request command
    # todo? - create a metric throttle command

    async def _reader(self) -> None:
        try:
            while True:
                body = await self.receive_bytes()

                # todo? improve this logic to detect if the device has been deleted?
                device = await self.authenticator()

                telemetry = Telemetry.unpack(body)
                await self.metrics_server.telemetry(telemetry, device)

                # todo - only send time sync command if time delta is too large
                now = int(time.time() * 1000)  # todo move this into writer?
                await self.queue.put(SetTimeCommand(now))

        except WebSocketDisconnect as wsd:
            logger.info(wsd)
        except HTTPException as he:
            if he.status_code in (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_404_NOT_FOUND,
            ):
                # todo? - send a ReregisterCommand rather than just disconnecting
                #         the client and letting it decide how to proceed when it
                #         tries to reconnect and it fails on the 401 or 404?
                pass
            else:
                raise

    async def _writer(self) -> None:
        while True:
            command = await self.queue.get()
            await self.send_bytes(command.pack())


@devices_router.websocket("/{device_id}/telemetry")
async def telemetry(
    websocket: WebSocket,
    device_id: int,
    metrics_server: MetricsServer = metrics_server,
    sessionmaker: SessionMaker = sessionmaker,
    device: DeviceORM = Depends(_authenticate_device_websocket),
) -> None:

    async def authenticator() -> DeviceORM:
        return await _authenticate_device_websocket(device_id, websocket, sessionmaker)

    await websocket.accept()
    async with TaskGroup() as task_group:
        telemetry_io = _TelemetryIO(
            metrics_server,
            websocket.receive_bytes,
            websocket.send_bytes,
            authenticator,
        )
        task_group.create_task(telemetry_io._reader())
        task_group.create_task(telemetry_io._writer())
