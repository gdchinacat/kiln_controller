import typing

import pydantic
import sqlmodel


class ORMType(sqlmodel.SQLModel):

    def validate_create_or_update(self) -> None:
        """validate the state of the new or updated resource"""

    def validate_delete(self) -> None:
        """validate the resource can be deleted"""
