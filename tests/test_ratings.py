"""Tests for ratings router."""
import pytest


@pytest.mark.anyio
async def test_get_ratings_returns_empty(client):
    response = await client.get("/api/v1/ratings/some-package")
    assert response.status_code == 200
    data = response.json()
    assert data["ratings"] == []
    assert data["average"] == 0.0


@pytest.mark.anyio
async def test_rating_summary(client):
    response = await client.get("/api/v1/ratings/some-package/summary")
    assert response.status_code == 200
    data = response.json()
    assert "distribution" in data
