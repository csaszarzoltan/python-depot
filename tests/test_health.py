"""Tests for health and root endpoints."""
import pytest


@pytest.mark.anyio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_returns_status(client):
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.anyio
async def test_root_returns_message(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "PythonDepot API"
    assert data["version"] == "0.1.0"
