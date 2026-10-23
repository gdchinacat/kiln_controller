import typing

import pydantic
import sqlmodel

from .validators import ValidatorMixinBase

if typing.TYPE_CHECKING:
    from .user import UserORM


class ORMType(sqlmodel.SQLModel, ValidatorMixinBase): ...
