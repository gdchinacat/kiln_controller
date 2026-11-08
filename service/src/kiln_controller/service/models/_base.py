import sqlmodel


class ORMType(sqlmodel.SQLModel):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    version: int = sqlmodel.Field(default=1)

    def validate_create_or_update(self) -> None:
        """validate the state of the new or updated resource"""

    def validate_delete(self) -> None:
        """validate the resource can be deleted"""
