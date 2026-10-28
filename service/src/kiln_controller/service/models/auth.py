from pydantic import BaseModel

__all__ = (
    "LoginRequest",
    "LogoutResponse",
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutResponse(BaseModel):
    pass
