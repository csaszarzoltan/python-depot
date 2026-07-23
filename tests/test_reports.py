"""Tests for reports router."""
import pytest


@pytest.mark.anyio
async def test_list_reports_returns_empty(client):
    response = await client.get("/api/v1/reports/")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data


@pytest.mark.anyio
async def test_get_report_by_year_month(client):
    response = await client.get("/api/v1/reports/2024/1")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["month"] == 1


@pytest.mark.anyio
async def test_generate_report(client):
    response = await client.post("/api/v1/reports/generate?year=2024&month=3")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"


@pytest.mark.anyio
async def test_get_report_html(client):
    response = await client.get("/api/v1/reports/2024/1/html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.anyio
async def test_list_reports_supports_year_filter(client):
    response = await client.get("/api/v1/reports/?year=2024")
    assert response.status_code == 200
