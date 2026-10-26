from fastapi import Depends, HTTPException, Request, status
from starlette.requests import HTTPConnection

from .metrics import MetricsServer
from .models import SessionMaker, UserORM

__all__ = (
    "current_user",
    "metrics_server",
    "sessionmaker",
)


@Depends
def metrics_server(ctx: HTTPConnection) -> MetricsServer:
    return ctx.app.state.metrics_server


@Depends
def sessionmaker(ctx: HTTPConnection) -> SessionMaker:
    return ctx.app.state.db_sessionmaker


@Depends
async def current_user(
    request: Request,
    sessionmaker: SessionMaker = sessionmaker,
) -> UserORM:
    """Get the currently authenticated user."""

    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with sessionmaker() as session:
        user = await session.get(UserORM, user_id)
        if not user:
            request.session.clear()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return user
