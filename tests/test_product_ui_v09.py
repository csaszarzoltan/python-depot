"""TDD acceptance tests for v0.9 persistent project workspaces."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from python_depot.product_ui import ProductUiService, render_product_page
from python_depot.routers import product_pages


def ui(tmp_path: Path) -> ProductUiService:
    return ProductUiService(tmp_path / "v09.db")


def test_create_project_imports_requirements_and_preserves_snapshot(
    tmp_path: Path,
) -> None:
    service = ui(tmp_path)
    project_id = service.create_project(
        "Checkout API",
        "payments/checkout",
        "requests>=2.31\nfastapi==0.110\n-e ./local",
    )
    project = service.project(project_id)
    assert project["name"] == "Checkout API"
    assert project["source"] == "payments/checkout"
    assert [item["name"] for item in project["dependencies"]] == ["fastapi", "requests"]
    assert project["ignored_lines"] == 1
    assert len(project["snapshots"]) == 1


def test_reimport_creates_new_snapshot_and_reports_delta(tmp_path: Path) -> None:
    service = ui(tmp_path)
    project_id = service.create_project("API", "repo/api", "requests==2.31\nflask==3.0")
    result = service.import_project_dependencies(
        project_id, "requests==2.32\nfastapi==0.111"
    )
    assert result["added"] == ["fastapi"]
    assert result["removed"] == ["flask"]
    assert result["changed"] == ["requests"]
    assert len(service.project(project_id)["snapshots"]) == 2


def test_projects_page_lists_saved_context_and_empty_state(tmp_path: Path) -> None:
    service = ui(tmp_path)
    empty = render_product_page("projects", service)
    assert "No projects yet" in empty
    project_id = service.create_project("API", "repo/api", "requests>=2")
    page = render_product_page("projects", service)
    assert "API" in page and "repo/api" in page
    assert f"/workspace/projects/{project_id}" in page


def test_project_detail_shows_dependencies_snapshot_and_reimport_form(
    tmp_path: Path,
) -> None:
    service = ui(tmp_path)
    project_id = service.create_project("API", "repo/api", "requests>=2")
    page = render_product_page("project-detail", service, {"project_id": project_id})
    assert "requests" in page
    assert "1 dependencies" in page
    assert "Import a new snapshot" in page
    assert f'action="/workspace/projects/{project_id}/import"' in page


def test_project_routes_create_and_redirect_to_detail(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "routes.db"
    monkeypatch.setattr(product_pages, "_DB", db)
    app = FastAPI()
    app.include_router(product_pages.router)
    client = TestClient(app)
    response = client.post(
        "/workspace/projects",
        data={"name": "API", "source": "repo/api", "dependencies": "requests>=2"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/workspace/projects/")
    detail = client.get(response.headers["location"])
    assert detail.status_code == 200 and "requests" in detail.text
