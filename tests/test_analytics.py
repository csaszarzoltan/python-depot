"""Tests for analytics router."""
import pytest


@pytest.mark.anyio
async def test_trending_packages(client):
    response = await client.get("/api/v1/analytics/trending")
    assert response.status_code == 200
    data = response.json()
    assert "trending" in data


@pytest.mark.anyio
async def test_popular_packages(client):
    response = await client.get("/api/v1/analytics/popular")
    assert response.status_code == 200
    data = response.json()
    assert "popular" in data


@pytest.mark.anyio
async def test_package_stats(client):
    response = await client.get("/api/v1/analytics/stats/some-package")
    assert response.status_code == 200
    data = response.json()
    assert data["views"] == 0
