"""
The application for the kiln_controller service.

Implements the resource model used by the UI and the devices.
Serves the SPA interface for the service.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sqlalchemy
import sqlalchemy.exc
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .metrics.victoriametrics import VictoriaMetricsServer
from .models import db  # initialize the database
from .models.validators import ValidationError
from .routers import (
    auth_router,
    devices_router,
    phases_router,
    schedules_router,
    users_router,
)

# debug
# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
# logging.getLogger("kiln_controller.client").setLevel(logging.INFO)
# end debug
logger = logging.getLogger("kiln_controller.app")

# By default an in memory non-persistent database is used so that tests and
# utilities don't accidentally modify the local database. The app must
# explicitly request the persistent database by setting the DB_URL envoronment
# variable when started.
SQLALCHEMY_DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
DB_URL = os.environ.get("DB_URL", SQLALCHEMY_DEFAULT_DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.state.db_engine = await db.get_engine(DB_URL)
    app.state.db_sessionmaker = db.get_sessionmaker(app.state.db_engine)
    yield


app = FastAPI(title="Kiln Controller", lifespan=lifespan)


app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "session secret"),
    https_only=True,
    same_site="lax",
)

app.state.metrics_server = VictoriaMetricsServer(
    "http://localhost:4242/api/put"
)

app.frontend("/", directory="./static")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
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
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": str(exc)},
    )


@app.exception_handler(Exception)
async def _default_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(exc)
    # todo - don't expose internal details (e) to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": str(exc)},
    )
