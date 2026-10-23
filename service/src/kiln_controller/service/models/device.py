"""
Device model.
"""

import hashlib
import hmac
import os
import secrets
from typing import Any, ClassVar

import pydantic
import sqlalchemy
import sqlmodel

from ._base import ResourceCreate, ORMType
from .user import UserORM
from .validators import DeviceValidator
from abc import ABC

__all__ = (
    "Device",
    "DeviceCreate",
    "DeviceCreateResponse",
    "DeviceUpdate",
    "DeviceORM",
    "FiringORM",  # hack until it's actually implemented (moves to firing.py)
)


NAME_LENGTH = 30


class _DeviceAuth(ABC):
    """Mixin to help manage device auth token."""

    AUTH_TOKEN_BYTES: ClassVar[int] = 32
    AUTH_TOKEN_LENGTH: ClassVar[int] = 64

    auth_token: str

    SECRET_KEY: ClassVar[bytes] = os.environ.get(
        "DEVICE_AUTH_HASH_KEY", "your_secure_environment_bound_secret_key"
    ).encode("utf-8")
    """The salt for hashed auth tokens."""

    @staticmethod
    def _auth_token_hash(token: str) -> str:
        """Get the hash for the token."""
        return hmac.new(
            _DeviceAuth.SECRET_KEY, token.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def validate_auth_token(self, auth_token: str) -> bool:
        """Validate the auth_token is valid for the hashed self.auth_token."""
        hash = self._auth_token_hash(auth_token)
        return hmac.compare_digest(hash, self.auth_token)

    @staticmethod
    def generate() -> tuple[str, str]:
        token = secrets.token_urlsafe(_DeviceAuth.AUTH_TOKEN_BYTES)
        return token, _DeviceAuth._auth_token_hash(token)


class DeviceCreate(ResourceCreate):
    """
    REST create model for Device.

    This is sent by the device and is intentionally minimmalistic.
    """

    name: str = pydantic.Field(max_length=NAME_LENGTH)
    user_id: int

    def extra_attrs(
        self, user: UserORM
    ) -> tuple[dict[str, str | int], dict[str, str | int]]:
        """provide the auth_token"""
        ret = super().extra_attrs(user)

        # Return the plaintext auth token to the device (ret[1]), but store the
        # hashed auth token in the database (ret[0]).
        ret[1]["auth_token"], ret[0]["auth_token"] = _DeviceAuth.generate()

        return ret


class DeviceCreateResponse(pydantic.BaseModel):
    id: int
    name: str
    auth_token: str = pydantic.Field(max_length=_DeviceAuth.AUTH_TOKEN_LENGTH)
    user_id: int


class DeviceUpdate(pydantic.BaseModel):
    """REST update model for Device."""

    name: str | None = pydantic.Field(default=None, max_length=NAME_LENGTH)
    user_id: int | None
    description: str | None


class Device(pydantic.BaseModel):
    """Rest model for Device."""

    id: int
    name: str
    user_id: int
    description: str | None = pydantic.Field(default=None)


class DeviceORM(DeviceValidator, ORMType, _DeviceAuth, table=True):
    __tablename__ = "devices"
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str = sqlmodel.Field(max_length=NAME_LENGTH)
    auth_token: str = sqlmodel.Field(
        nullable=False, max_length=_DeviceAuth.AUTH_TOKEN_LENGTH
    )

    """_plaintext_auth_token is an unmapped field that contains the plaintext
    auth_token. It exists only so newly created devices can return it to the
    client."""

    """The Bearer token the device must use to authenticate."""
    description: str | None = sqlmodel.Field(default=None)

    user_id: int = sqlmodel.Field(foreign_key="users.id")

    user: UserORM = sqlmodel.Relationship(
        back_populates="devices",
        sa_relationship_kwargs={"viewonly": True, "lazy": True},
    )
    """
    The user that manages the device (not the users with access to the device).
    """

    ###
    # Hack FiringORM in to avovid having to come back to victoriametrics in a bit
    class FiringORM:
        """stub for now...metrics needs it"""

        id = 0

    firing: ClassVar[Any] = FiringORM()


FiringORM = DeviceORM.FiringORM
### End FiringORM hack
