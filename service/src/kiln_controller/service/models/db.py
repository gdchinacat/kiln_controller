"""
The SQLAlchemy database.
"""

import asyncio
import os

from sqlalchemy import inspect, Connection
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlmodel import SQLModel

from .device import *
from .schedule import *
from .user import *

__all__ = (
    "get_engine",
    "get_sessionmaker",
)


ADMIN_NAME = "Admin User"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# By default an in memory non-persistent database is used so that tests and
# utilities don't accidentally modify the local database. The app must
# explicitly request the persistent database.
SQLALCHEMY_DEFAULT_DATABASE_URL = "sqlite+aiosqlite://"


type SessionMaker = async_sessionmaker[AsyncSession]


async def get_engine(uri: str = SQLALCHEMY_DEFAULT_DATABASE_URL) -> AsyncEngine:
    """Engine factory."""
    engine = create_async_engine(uri)

    async with engine.connect() as connection:
        initialize = await connection.run_sync(_needs_initialization)
        await connection.run_sync(SQLModel.metadata.create_all)

    if initialize:
        async with get_sessionmaker(engine)() as session:
            session.add(
                UserORM(
                    name=ADMIN_NAME, username=ADMIN_USERNAME, password=ADMIN_PASSWORD
                )
            )
            await session.commit()
    return engine


def get_sessionmaker(engine: AsyncEngine) -> SessionMaker:
    """Session factory dependency."""
    return async_sessionmaker(engine, expire_on_commit=False)


def _needs_initialization(connection: Connection) -> bool:
    # inspect the database to see if it should be initialized.
    inspector = inspect(connection)
    return not inspector.has_table(UserORM.__tablename__)
