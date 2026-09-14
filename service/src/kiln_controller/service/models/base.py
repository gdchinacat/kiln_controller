"""
Base class for mapped resources.
"""

from typing import ClassVar, Any

from pydantic import BaseModel
from sqlmodel import SQLModel, Field

from .validators import ValidatorMixinBase


__all__ = ("Base", "MappedBase")


class Base(ValidatorMixinBase, BaseModel):
    """
    Base class for all ORM models.
    """

    id: int | None = Field(default=None, primary_key=True)
    """
    All model dataclasses contain a primary key named id.
    id is optional only to support database assignment.
    """

    name: str = Field(max_length=30)
    """all model dataclasses contain a name"""

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
    """exists primarily for typing"""
