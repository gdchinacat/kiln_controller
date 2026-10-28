from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..dependencies import current_user, sessionmaker
from ..models import (
    LoginRequest,
    LogoutResponse,
    SessionMaker,
    User,
    UserORM,
)

__all__ = ("auth_router",)


auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.get("/me")
async def me(user: User = current_user) -> User:
    return user


@auth_router.post("/login", response_model=User)
async def login(
    login: LoginRequest,
    request: Request,
    sessionmaker: SessionMaker = sessionmaker,
) -> UserORM:
    query = select(UserORM).where(UserORM.username == login.username)  # type: ignore
    async with sessionmaker() as session:
        user = (await session.execute(query)).scalars().first()
        if user is None or not user.verify_password(login.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    request.session["user_id"] = user.id
    return user


@auth_router.api_route("/logout", methods=["GET", "POST"])
async def logout(
    request: Request,
) -> LogoutResponse:
    if request.session:
        request.session["user_id"] = None
    return LogoutResponse()
