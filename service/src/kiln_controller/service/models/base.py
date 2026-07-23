"""
Base class for mapped resources.
"""

from typing import ClassVar, Any
from sqlmodel import SQLModel, Field


class Base(SQLModel):
    """
    Base class for all ORM models.
    """

    __public_fields__: ClassVar[set[str]] = {"id", "name"}
    """
    The attributes that should be serialized.
    """

    id: int | None = Field(default=None, primary_key=True)
    """
    All model dataclasses contain a primary key named id.
    id is optional only to support database assignment.
    """

    name: str = Field(max_length=30)
    """all model dataclasses contain a name"""

    def asdict(self) -> dict[str, Any]:  # todo TypedDict based on pydantic model?
        """Serialize the model to a JSON-safe dict of public fields."""
        return self.model_dump(mode="json", include=self.__public_fields__)

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
