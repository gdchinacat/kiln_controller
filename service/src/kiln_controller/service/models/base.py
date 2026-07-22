"""
Base class for mapped resources.
"""

from typing import ClassVar, Dict, Optional
from sqlmodel import SQLModel, Field


class Base(SQLModel):
    """
    Base class for all ORM models.

    Uses SQLModel which combines SQLAlchemy with Pydantic to provide
    automatic field validation without requiring manual validation code.
    """

    PUBLIC_FIELDS: ClassVar[Dict] = {"id": None, "name": None}
    """
    Subclasses must include the fields they want to expose through api.

    Keys are field name.
    Values are the marshalling function for the field (type conversion). None
    means marshal as is.
    """

    model_config = {"arbitrary_types_allowed": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    """all model dataclasses contain a primary key named id"""

    name: str = Field(max_length=30)
    """all model dataclasses contain a name"""

    def asdict(self):
        """marshal the model as a json dict"""
        return {
            name: (marshaler or (lambda x: x))(getattr(self, name))
            for (name, marshaler) in self.PUBLIC_FIELDS.items()
        }

    def validate_create_or_update(self):
        """
        Validate this resource is valid and in a consistent state. Called
        by the Resource or children ResourceList classes when updated.

        raises ValidationError when the validation fails.
        """

    def validate_delete(self):
        """
        Validate this resource can be deleted.

        raises ValidationError when the validation fails.
        """