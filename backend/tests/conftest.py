import pytest
import asyncio
from database import engine
from core.security import login_rate_limiter, login_ip_rate_limiter, register_rate_limiter

@pytest.fixture(autouse=True)
async def cleanup_engine():
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Aísla cada test: los limitadores en memoria no deben arrastrar intentos entre pruebas."""
    for limiter in (login_rate_limiter, login_ip_rate_limiter, register_rate_limiter):
        limiter.reset()
    yield
    for limiter in (login_rate_limiter, login_ip_rate_limiter, register_rate_limiter):
        limiter.reset()
