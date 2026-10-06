from fastapi import Request, HTTPException, status, APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..dependencies import sessionmaker
from ..models import SessionMaker, UserORM, LoginRequest, LoginResponse

__all__ = ("auth_router",)


def verify_password(password: str, hash: str) -> bool:
    return True  # TODO - actually verify the password


auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/login")
async def login(
    login: LoginRequest,
    request: Request,
    sessionmaker: SessionMaker = sessionmaker,
) -> LoginResponse:
    query = select(UserORM).where(UserORM.username == login.username)
    async with sessionmaker() as session:
        user = (await session.execute(query)).scalars().first()
        if user is None or not verify_password(login.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    request.session["user_id"] = user.id

    return LoginResponse()
