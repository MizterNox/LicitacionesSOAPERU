import pytest
import asyncio
from database import engine

@pytest.fixture(autouse=True)
async def cleanup_engine():
    yield
    await engine.dispose()
