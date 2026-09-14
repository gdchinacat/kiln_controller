"""
Device related Flask resources
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..models import Device, DeviceORM, Session
from .base import create_router

security = HTTPBasic()


devices_router = create_router(Device, DeviceORM)


async def _authenticate_device(
    device_id: int, credentials: HTTPBasicCredentials = Depends(security)
) -> Device:
    if str(device_id) == credentials.username:
        with Session() as session:
            device = session.get(DeviceORM, device_id)
            if device:
                return device
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
    )


@devices_router.put("/{device_id}/telemetry")
async def telemetry(device_id: str, device: Device = Depends(_authenticate_device)):
    # TODO - implement binary telemetry protocol
    # TODO - logic should be on Device
    return bytes()
