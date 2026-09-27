"""
Device related Flask resources
"""

import logging
import time
from functools import partial

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

from ...device.protocol import Telemetry, SetTimeCommand
from ..models import (
    Device,
    DeviceCreate,
    DeviceCreateResponse,
    DeviceUpdate,
    DeviceORM,
    Session,
    User,
    Session,
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
) -> Device:
    auth_header = websocket.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ")[1]

        with Session() as session:
            device_orm = session.get(DeviceORM, device_id)
            if not device_orm:
                # todo - is it OK to expose this as 404 without auth passing to let
                #        the device know it needs to re-register?
                # todo - no test failed when this 401 was changed to 404, need test
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            if device_orm.auth_token == auth_token:
                return Device.model_validate(device_orm.model_dump())
    raise HTTPException(
        # todo - don't send json auth errors
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@devices_router.websocket("/{device_id}/telemetry")
async def telemetry(
    websocket: WebSocket,
    device_id: int,
    device: Device = Depends(_authenticate_device_websocket),
) -> None:

    await websocket.accept()
    # todo - send a time sync on connection

    # todo - change from request/response model to full bidirectional mode
    # todo - create a task for sending commands
    # todo? - create a metric request command
    # todo? - create a metric throttle command

    try:
        while True:
            body = await websocket.receive_bytes()

            # todo? improve this logic to detect if the device has been deleted?
            await _authenticate_device_websocket(device_id, websocket)
            telemetry = Telemetry.unpack(body)

            delta = telemetry.timestamp_ms - int(time.time() * 1000)
            logger.error(f"device {device.id} telemetry delta {delta}")

            now = int(time.time() * 1000)
            await websocket.send_bytes(SetTimeCommand(now).pack())
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
