"""
The application for the kiln_controller service.

Implements the resource model used by the UI and the devices.
Serves the SPA interface for the service.
"""

from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import pydantic
import sqlalchemy

from .models import db  # initialize the database
from .routers import users_router, devices_router, schedules_router, phases_router
from .models.validators import ValidationError

logger = logging.getLogger("kiln_controller.app")

# debug
# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
# logging.getLogger("kiln_controller.client").setLevel(logging.INFO)
# end debug

app = FastAPI()
app.frontend("/", directory="./static")
app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.exception_handler(sqlalchemy.exc.IntegrityError)
async def _integrity_error_handler(
    request: Request, exc: sqlalchemy.exc.IntegrityError
) -> JSONResponse:
    # todo - we should not be getting IntegrityErrors from the database
    #        since that indicates validation was lacking. But...that's
    #        going to happen, so handle it as a *client* error since
    #        the model is simple enough to make that a good assumption.
    # todo - don't expose internal details (e) to client
    logger.exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(exc)}
    )


@app.exception_handler(Exception)
async def _default_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(exc)
    # todo - don't expose internal details (e) to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(exc)}
    )
