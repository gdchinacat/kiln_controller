from dataclasses import asdict
from typing import Annotated
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column, Mapped

primary_key = Annotated[int, mapped_column(primary_key=True)]
name_field = Annotated[str, mapped_column(String(30))]

class Base(MappedAsDataclass, DeclarativeBase):
    """subclasses will be converted to dataclasses"""
    
    # all resource dataclasses contain a primary key named id
    id: Mapped[primary_key] = mapped_column(primary_key=True, default=None, kw_only=True)

    def asdict(self):
        return asdict(self)