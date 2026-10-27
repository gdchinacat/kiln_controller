from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..dependencies import sessionmaker
from ..models import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionMaker,
    UserORM,
)

__all__ = ("auth_router",)


auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/login")
async def login(
    login: LoginRequest,
    request: Request,
    sessionmaker: SessionMaker = sessionmaker,
) -> LoginResponse:
    query = select(UserORM).where(UserORM.username == login.username)  # type: ignore
    async with sessionmaker() as session:
        user = (await session.execute(query)).scalars().first()
        if user is None or not user.verify_password(login.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    request.session["user_id"] = user.id

    return LoginResponse()


@auth_router.post("/logout")
async def logout(
    request: Request,
    sessionmaker: SessionMaker = sessionmaker,
) -> LogoutResponse:
    del request.session["user_id"]
    return LogoutResponse()
