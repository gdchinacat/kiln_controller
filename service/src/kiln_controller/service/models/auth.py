from pydantic import BaseModel

__all__ = (
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    pass


class LogoutResponse(BaseModel):
    pass
