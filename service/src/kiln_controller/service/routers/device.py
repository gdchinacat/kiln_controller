"""
Device related Flask resources
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..models import Device, DeviceUpdate, DeviceORM, Session
from .base import create_router, SKIP, authenticate_user

security = HTTPBasic()


devices_router = create_router(
    "device",
    Device,
    DeviceORM,
    resource_update_type=DeviceUpdate,
    resource_create_type=SKIP,
)


async def _authenticate_device(
    device_id: int, credentials: HTTPBasicCredentials = Depends(security)
) -> Device:
    if str(device_id) == credentials.username:
        with Session() as session:
            device = session.get(DeviceORM, device_id)
            # todo actually verify the device password matches
            if device and (True and device.password == credentials.password):
                return device
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@devices_router.post("/")
async def create_device(device: Device = Depends(authenticate_user)):
    return bytes()


@devices_router.put("/{device_id}/telemetry")
async def telemetry(device_id: int, device: Device = Depends(_authenticate_device)):
    # TODO - implement binary telemetry protocol
    # TODO - logic should be on Device
    return bytes()
