"""
The application for the kiln_controller service.

Implements the resource model used by the UI and the devices.
Serves the SPA interface for the service.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .models import db  # initialize the database
from .routers import users_router, devices_router, schedules_router, phases_router
from ..common import ValidationError

# debug
import logging

logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("kiln_controller.client").setLevel(logging.INFO)
# end debug

app = FastAPI()
app.frontend("/", directory="./static")

app.include_router(users_router)
app.include_router(devices_router)
app.include_router(schedules_router)
app.include_router(phases_router)


@app.exception_handler(ValidationError)
async def _validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=exc.json()
    )
