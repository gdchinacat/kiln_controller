import pytest

from sqlalchemy.ext.asyncio import AsyncEngine
from kiln_controller.service.models import get_engine, get_sessionmaker, SessionMaker


@pytest.fixture
async def engine() -> AsyncEngine:
    return await get_engine("sqlite+aiosqlite://")


@pytest.fixture
def sessionmaker(engine: AsyncEngine) -> SessionMaker:
    return get_sessionmaker(engine)
