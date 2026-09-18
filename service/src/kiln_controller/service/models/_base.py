import pydantic

import typing

if typing.TYPE_CHECKING:
    from .user import UserORM


class ResourceCreate(pydantic.BaseModel):
    def extra_attrs(self, user: UserORM) -> dict[str, str | int]:
        return {}
