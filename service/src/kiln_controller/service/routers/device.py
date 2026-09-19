"""
Device related Flask resources
"""

from functools import partial

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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


async def _authenticate_device(
    device_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> Device:
    with Session() as session:
        device_orm = session.get(DeviceORM, device_id)
        if device_orm and device_orm.auth_token == credentials.credentials:
            return Device.model_validate(device_orm.model_dump())
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


binary_route = partial(
    devices_router.post, responses={200: {"content": {"application/octet-stream": {}}}}
)


class OctetStreamResponse(Response):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, media_type="application/octet-stream")


@binary_route("/{device_id}/telemetry")
async def telemetry(
    device_id: int, device: Device = Depends(_authenticate_device)
) -> OctetStreamResponse:
    # TODO - implement binary telemetry protocol
    # TODO - logic should be on Device
    return OctetStreamResponse(b"")
