"""
The SQLAlchemy database.
"""

import os

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .device import *
from .schedule import *
from .user import *

__all__ = tuple()


ADMIN_NAME = "Admin User"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# NON_PERSISTENT=true env variable specifies that an in-memory database should
# be used. Only recommended for unit testing.
if os.getenv("NON_PERSISTENT", "false").upper() == "TRUE":
    SQLALCHEMY_DATABASE_URI = "sqlite://"
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///kiln_controller.db"

_engine = create_engine(SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=_engine)

# inspect the database to see if it should be initialized.
inspector = inspect(_engine)
initialize = not inspector.has_table(UserORM.__tablename__)

SQLModel.metadata.create_all(_engine.engine)
if initialize:
    with Session() as session:
        session.add(
            UserORM(name=ADMIN_NAME, username=ADMIN_USERNAME, password=ADMIN_PASSWORD)
        )
        session.commit()
