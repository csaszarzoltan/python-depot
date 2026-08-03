"""Shared test fixtures."""
import os
import tempfile
from pathlib import Path

# Per-process DB isolation: parallel kanban workers (tester, tech-lead,
# documenter) previously raced on the hardcoded /tmp/python_depot.db,
# causing "table already exists" / "no such table" flakiness. Each pytest
# process gets its own temp DB file (env var must be set BEFORE the
# python_depot.database import below, which creates the engine eagerly).
_db_dir = Path(tempfile.mkdtemp(prefix="python_depot_test_"))
os.environ["PYTHON_DEPOT_DATABASE_URL"] = f"sqlite:///{_db_dir / 'test.db'}"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from python_depot.database import reset_db  # noqa: E402
from src.app import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_db():
    """Drop and recreate all tables before each test for isolation."""
    reset_db()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Provide an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
