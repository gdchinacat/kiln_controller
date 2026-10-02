from fastapi import Request, WebSocket, Depends
from starlette.requests import HTTPConnection
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .models import SessionMaker
from .metrics import MetricsServer

__all__ = (
    "sessionmaker",
    "metrics_server",
)


@Depends
def sessionmaker(ctx: HTTPConnection) -> SessionMaker:
    return ctx.app.state.db_sessionmaker


@Depends
def metrics_server(websocket: WebSocket) -> MetricsServer:
    return websocket.app.state.metrics_server
