from pydantic import BaseModel

__all__ = (
    "LoginRequest",
    "LoginResponse",
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    pass
