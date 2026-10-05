import typing

import pydantic
import sqlmodel

from .validators import ValidatorMixinBase

if typing.TYPE_CHECKING:
    from .user import UserORM


class ResourceCreate(pydantic.BaseModel):
    def extra_attrs(
        self, user: UserORM
    ) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
        """
        Get the server-assigned attributes to be added to the models for create
        resource routes. return is a 2-tuple, the first element are added to
        the ORM creation, the second to the response."""
        return {}, {}


class ORMType(sqlmodel.SQLModel, ValidatorMixinBase): ...
