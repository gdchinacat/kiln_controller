from typing import Annotated
from sqlalchemy import String
from sqlalchemy.orm import (DeclarativeBase, MappedAsDataclass, mapped_column,
                            Mapped)


primary_key = Annotated[int, mapped_column(primary_key=True)]
name_field = Annotated[str, mapped_column(String(30))]


class Base(MappedAsDataclass, DeclarativeBase):
    """subclasses will be converted to dataclasses"""

    PUBLIC_FIELDS = {'id': None,
                     'name': None}
    """
    Subclasses must include the fields they want to expose through api.

    Keys are field name.
    Values are the marshalling function for the field (type conversion). None
    means marshal as is.
    """

    name: Mapped[name_field]
    """all model dataclasses contain a name"""

    id: Mapped[primary_key] = mapped_column(primary_key=True, default=None,
                                            kw_only=True)
    """all model dataclasses contain a primary key named id"""

    def asdict(self):
        '''marshal the model as a json dict'''
        return {name: getattr(self, name) for name in self.PUBLIC_FIELDS}
