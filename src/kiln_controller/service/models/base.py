'''
Base class for mapped resources.
'''
from sqlalchemy import String
from sqlalchemy.orm import (DeclarativeBase, MappedAsDataclass, mapped_column,
                            Mapped)


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

    name: Mapped[str] = mapped_column(String(30))
    """all model dataclasses contain a name"""

    id: Mapped[int] = mapped_column(primary_key=True, default=None,
                                    kw_only=True)
    """all model dataclasses contain a primary key named id"""

    def asdict(self):
        '''marshal the model as a json dict'''
        return {name: (marshaler or (lambda x: x))(getattr(self, name))
                for (name, marshaler) in self.PUBLIC_FIELDS.items()}

    def validate(self):
        '''
        Validate this resource is valid and in a consistent state. It is called
        by the Resource or children ResourceList classes when updated.

        raises ValidationError when the validation fails.
        '''
        pass
