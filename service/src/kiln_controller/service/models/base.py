"""
Base class for mapped resources.
"""

from typing import ClassVar, Any

import pydantic
from sqlmodel import SQLModel, Field

from .validators import ValidatorMixinBase

__all__ = ("Base", "BaseUpdate", "MappedBase")


MAX_NAME_LENGTH = 30


class BaseUpdate(pydantic.BaseModel):
    """
    Base class for all models.

    The "Update" version is the base class because it is the least restrictive
    version.
    """

    """
    TODO I don't want id on the create resources, but they all currently extend from
    this.
    """
    id: int | None = None
    name: str | None = pydantic.Field(default=None, max_length=MAX_NAME_LENGTH)


class Base(ValidatorMixinBase, BaseUpdate):
    """
    Base class for all models.
    """

    id: int
    """
    All model dataclasses contain a primary key named id.
    """

    name: str = pydantic.Field(max_length=MAX_NAME_LENGTH)
    """
    The name of the resource.

    The name is what users call the resource.
    """

    def validate_create_or_update(self) -> None:
        """
        Validate this resource is valid and in a consistent state. Called
        by the Resource or children ResourceList classes when updated.

        raises ValidationError when the validation fails.
        """

    def validate_delete(self) -> None:
        """
        Validate this resource can be deleted.

        raises ValidationError when the validation fails.
        """


class MappedBase(Base, SQLModel):
    """
    Base class for resource ORMs.
    """

    # While it would be better to not have this optional, it needs to exist in
    # a state while not set to be validated during create and added to the
    # session to get the server assigned id. It is possible to have two mapped
    # versions,  one with and one without so that adding the MappedBaseWithoutId
    # will create the # MappedBaseWithID. This is a lot simpler and works just
    # as well. Practicality beats purity for now. todo?
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=MAX_NAME_LENGTH)
