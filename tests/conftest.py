"""Shared test fixtures."""
import pytest
from httpx import ASGITransport, AsyncClient

from python_depot.database import reset_db
from src.app import app


@pytest.fixture(autouse=True)
def _clean_db():
    """Drop and recreate all tables before each test for isolation."""
    reset_db()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
