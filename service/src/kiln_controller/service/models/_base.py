import typing

import pydantic
import sqlmodel

from .validators import ValidatorMixinBase

if typing.TYPE_CHECKING:
    from .user import UserORM


class ResourceCreate(pydantic.BaseModel):
    def extra_attrs(
        self, user: UserORM
    ) -> dict[str, str | int]:  # todo this should't inject user to everything
        return {}


class ORMType(sqlmodel.SQLModel, ValidatorMixinBase): ...
