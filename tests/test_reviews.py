"""Tests for reviews router."""
import pytest


@pytest.mark.anyio
async def test_list_reviews_returns_empty(client):
    response = await client.get("/api/v1/reviews/some-package")
    assert response.status_code == 200
    data = response.json()
    assert data["reviews"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_get_review_not_found(client):
    response = await client.get("/api/v1/reviews/some-package/1")
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
