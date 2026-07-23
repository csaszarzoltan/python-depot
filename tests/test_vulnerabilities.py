"""Tests for vulnerabilities router."""
import pytest


@pytest.mark.anyio
async def test_list_scans_returns_empty(client):
    response = await client.get("/api/v1/vulnerabilities/some-package")
    assert response.status_code == 200
    data = response.json()
    assert data["scans"] == []


@pytest.mark.anyio
async def test_trigger_scan(client):
    response = await client.post("/api/v1/vulnerabilities/some-package/scan")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scan_queued"
