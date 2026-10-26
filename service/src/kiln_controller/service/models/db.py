"""
The SQLAlchemy database.
"""

from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
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

type SessionMaker = async_sessionmaker[AsyncSession]


async def get_engine(uri: str) -> AsyncEngine:
    """Engine factory."""
    engine = create_async_engine(uri)

    async with engine.connect() as connection:
        initialize = await connection.run_sync(_needs_initialization)
        await connection.run_sync(SQLModel.metadata.create_all)

    if initialize:
        async with get_sessionmaker(engine)() as session:
            session.add(
                UserORM(
                    name=ADMIN_NAME,
                    username=ADMIN_USERNAME,
                    password=ADMIN_PASSWORD,
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
