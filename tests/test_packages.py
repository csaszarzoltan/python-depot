"""Tests for packages router — updated for new behavioral contract."""
import pytest


@pytest.mark.anyio
async def test_list_packages_returns_empty(client):
    response = await client.get("/api/v1/packages/")
    assert response.status_code == 200
    data = response.json()
    assert data["packages"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_get_package_not_found(client):
    response = await client.get("/api/v1/packages/nonexistent")
    # Per the behavioural contract non-existent packages return 404
    assert response.status_code == 404
