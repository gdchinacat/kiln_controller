"""
The SQLAlchemy database.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from .device import *
from .schedule import *
from .user import *

# NON_PERSISTENT=true env variable specifies that an in-memory database should
# be used. Only recommended for unit testing.
if os.getenv("NON_PERSISTENT", "false").upper() == "TRUE":
    SQLALCHEMY_DATABASE_URI = "sqlite://"
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///kiln_controller.db"

_engine = create_engine(SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=_engine)

SQLModel.metadata.create_all(_engine.engine)
