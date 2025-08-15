from dataclasses import asdict
from typing import Annotated
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column

primary_key = Annotated[int, mapped_column(primary_key=True)]
name_field = Annotated[str, mapped_column(String(30))]

class Base(MappedAsDataclass, DeclarativeBase):
    """subclasses will be converted to dataclasses"""

    def asdict(self):
        return asdict(self)