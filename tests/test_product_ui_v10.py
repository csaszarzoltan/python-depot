"""TDD acceptance tests for v0.10 cross-workspace project context reuse."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from python_depot.product_ui import ProductUiService, render_product_page
from python_depot.routers import product_pages


def ui(tmp_path: Path) -> ProductUiService:
    return ProductUiService(tmp_path / "v10.db")


def test_project_detail_offers_contextual_next_actions(tmp_path: Path) -> None:
    service = ui(tmp_path)
    project_id = service.create_project(
        "Checkout API", "team/checkout", "requests>=2\nfastapi"
    )
    page = render_product_page("project-detail", service, {"project_id": project_id})
    assert f"/workspace/projects/{project_id}/upgrade" in page
    assert f"/workspace/projects/{project_id}/compare" in page
    assert "/workspace/risk-inbox?q=Checkout+API" in page
    assert "Analyze Python upgrade" in page
    assert "Compare dependencies" in page


def test_project_upgrade_route_prefills_saved_dependency_input(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "routes.db"
    monkeypatch.setattr(product_pages, "_DB", db)
    project_id = ProductUiService(db).create_project(
        "API", "team/api", "requests>=2\nfastapi"
    )
    app = FastAPI()
    app.include_router(product_pages.router)
    response = TestClient(app).get(
        f"/workspace/projects/{project_id}/upgrade?target=3.12"
    )
    assert response.status_code == 200
    assert "requests&gt;=2" in response.text
    assert "fastapi" in response.text
    assert "2 dependencies detected" in response.text
    assert "<option selected>3.12</option>" in response.text


def test_project_compare_route_prefills_distinct_dependencies(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "routes.db"
    monkeypatch.setattr(product_pages, "_DB", db)
    project_id = ProductUiService(db).create_project(
        "API", "team/api", "requests>=2\nfastapi"
    )
    app = FastAPI()
    app.include_router(product_pages.router)
    response = TestClient(app).get(f"/workspace/projects/{project_id}/compare")
    assert response.status_code == 200
    assert "Compare dependencies for API" in response.text
    assert "fastapi, requests" in response.text
    assert "Evidence pending" in response.text


def test_project_context_launches_emit_privacy_safe_telemetry(tmp_path: Path) -> None:
    service = ui(tmp_path)
    project_id = service.create_project("API", "secret/repo", "private-package>=1")
    service.track_project_workflow(project_id, "upgrade")
    event = service.telemetry_events()[-1]
    assert event["event_type"] == "project_workflow_opened"
    assert project_id in event["properties"]
    assert "secret/repo" not in event["properties"]
    assert "private-package" not in event["properties"]


def test_missing_project_context_route_returns_404(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(product_pages, "_DB", tmp_path / "missing.db")
    app = FastAPI()
    app.include_router(product_pages.router)
    client = TestClient(app)
    assert client.get("/workspace/projects/missing/upgrade").status_code == 404
    assert client.get("/workspace/projects/missing/compare").status_code == 404
