"""
The application for the kiln_controller service.

Implements the resource model used by the UI and the devices.
Serves the SPA interface for the service.
"""

from collections.abc import Iterable, AsyncIterator
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import pydantic
import sqlalchemy

from .metrics.victoriametrics import VictoriaMetricsServer
from .models import db  # initialize the database
from .models.validators import ValidationError
from .routers import users_router, devices_router, schedules_router, phases_router

SQLALCHEMY_PERSISTENT_DATABASE_URL = "sqlite+aiosqlite:///kiln_controller.db"

# debug
# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
# logging.getLogger("kiln_controller.client").setLevel(logging.INFO)
# end debug

logger = logging.getLogger("kiln_controller.app")

if os.environ.get("TEST_SERVICE", "false").upper() == "TRUE":
    url = db.SQLALCHEMY_DEFAULT_DATABASE_URL
else:
    url = SQLALCHEMY_PERSISTENT_DATABASE_URL


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db_engine = await db.get_engine(url)
    app.state.db_sessionmaker = db.get_sessionmaker(app.state.db_engine)
    yield


app = FastAPI(title="Kiln Controller", lifespan=lifespan)

app.frontend("/", directory="./static")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.metrics_server = VictoriaMetricsServer("http://localhost:4242/api/put")


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
