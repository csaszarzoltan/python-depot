"""FastAPI page routes for the six PythonDepot product workspaces."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from python_depot.product_ui import ProductUiService, render_product_page

router = APIRouter()
_DB = Path(os.getenv("PYTHONDEPOT_PRODUCT_DB", "/tmp/python_depot_product.db"))


def _service() -> ProductUiService:
    return ProductUiService(_DB)


@router.get("/workspace/{page}", response_class=HTMLResponse)
def product_workspace(page: str, request: Request) -> HTMLResponse:
    """Render a product workspace and its empty, status, and recovery states."""
    try:
        payload = (
            {
                "query": request.query_params.get("q", ""),
                "state": request.query_params.get("state", "ALL"),
                "notice": request.query_params.get("notice", "Ready"),
            }
            if page == "risk-inbox"
            else {"notice": request.query_params.get("notice", "Ready")}
        )
        return HTMLResponse(render_product_page(page, _service(), payload))
    except KeyError:
        return HTMLResponse("Product workspace not found", status_code=404)


@router.post("/workspace/decisions", response_class=HTMLResponse)
def decision_workspace_submit(
    purpose: str = Form(...), candidates: str = Form(...)
) -> HTMLResponse:
    items = [item.strip() for item in candidates.split(",") if item.strip()]
    normalized = {item.lower().replace("_", "-") for item in items}
    errors = []
    if len(items) < 2 or len(normalized) < 2:
        errors.append("Add at least two distinct packages.")
    payload = {"purpose": purpose.strip(), "candidates": items, "errors": errors}
    return HTMLResponse(
        render_product_page("decisions", _service(), payload),
        status_code=422 if errors else 200,
    )


@router.post("/workspace/upgrade", response_class=HTMLResponse)
def upgrade_workspace_submit(
    target_python: str = Form(...), dependencies: str = Form(...)
) -> HTMLResponse:
    value: dict[str, object] = {
        "target_python": target_python,
        "dependency_input": dependencies,
    }
    return HTMLResponse(render_product_page("upgrade", _service(), value))


@router.post("/workspace/risk-inbox/{item_id}/state")
def update_risk_state(
    item_id: str,
    state: str = Form(...),
    return_query: str = Form(""),
    return_state: str = Form("ALL"),
    note: str = Form(""),
    owner: str | None = Form(None),
    due_date: str | None = Form(None),
) -> RedirectResponse:
    """Update one risk and return to the user's filtered inbox."""
    try:
        _service().update_risk_item(
            item_id, state, note=note, owner=owner, due_date=due_date
        )
        notice = "Risk updated"
    except (KeyError, ValueError):
        notice = "Risk update failed"
    query = urlencode({"q": return_query, "state": return_state, "notice": notice})
    return RedirectResponse(f"/workspace/risk-inbox?{query}", status_code=303)


@router.get("/workspace/risk-inbox/{item_id}", response_class=HTMLResponse)
def risk_detail(item_id: str) -> HTMLResponse:
    """Show a single risk with ownership and immutable activity history."""
    try:
        return HTMLResponse(
            render_product_page("risk-detail", _service(), {"item_id": item_id})
        )
    except KeyError:
        return HTMLResponse("Risk item not found", status_code=404)


@router.post("/workspace/risk-inbox/bulk")
def bulk_update_risk_state(
    item_ids: list[str] = Form(...),
    state: str = Form(...),
    note: str = Form(""),
    return_query: str = Form(""),
    return_state: str = Form("ALL"),
) -> RedirectResponse:
    """Atomically update selected risks and preserve the active inbox view."""
    try:
        result = _service().bulk_update_risk_items(item_ids, state, note=note)
        notice = f"{result['updated']} risks updated"
    except (KeyError, ValueError):
        notice = "Bulk update failed; no risks changed"
    query = urlencode({"q": return_query, "state": return_state, "notice": notice})
    return RedirectResponse(f"/workspace/risk-inbox?{query}", status_code=303)


@router.post("/workspace/projects")
def create_project(
    name: str = Form(...), source: str = Form(...), dependencies: str = Form(...)
) -> RedirectResponse:
    """Create a persistent project and redirect to its first snapshot."""
    try:
        project_id = _service().create_project(name, source, dependencies)
    except ValueError:
        return RedirectResponse(
            "/workspace/projects?notice=Project+validation+failed", status_code=303
        )
    return RedirectResponse(f"/workspace/projects/{project_id}", status_code=303)


@router.get("/workspace/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: str, request: Request) -> HTMLResponse:
    """Render the current dependency snapshot and import history."""
    try:
        return HTMLResponse(
            render_product_page(
                "project-detail",
                _service(),
                {
                    "project_id": project_id,
                    "change_notice": request.query_params.get("notice", ""),
                },
            )
        )
    except KeyError:
        return HTMLResponse("Project not found", status_code=404)


@router.post("/workspace/projects/{project_id}/import")
def import_project_snapshot(
    project_id: str, dependencies: str = Form(...)
) -> RedirectResponse:
    """Import a new snapshot and summarize its dependency delta."""
    try:
        result = _service().import_project_dependencies(project_id, dependencies)
        notice = (
            f"{len(result['added'])} added, {len(result['removed'])} removed, "
            f"{len(result['changed'])} changed"
        )
    except KeyError:
        return RedirectResponse(
            "/workspace/projects?notice=Project+not+found", status_code=303
        )
    return RedirectResponse(
        f"/workspace/projects/{project_id}?{urlencode({'notice': notice})}",
        status_code=303,
    )


@router.get("/workspace/projects/{project_id}/upgrade", response_class=HTMLResponse)
def project_upgrade(project_id: str, request: Request) -> HTMLResponse:
    """Open the upgrade planner with the project's latest dependency snapshot."""
    service = _service()
    try:
        project = service.project(project_id)
        service.track_project_workflow(project_id, "upgrade")
    except KeyError:
        return HTMLResponse("Project not found", status_code=404)
    return HTMLResponse(
        render_product_page(
            "upgrade",
            service,
            {
                "target_python": request.query_params.get("target", "3.13"),
                "dependency_input": project["raw_input"],
                "notice": f"Using latest snapshot from {project['name']}",
            },
        )
    )


@router.get("/workspace/projects/{project_id}/compare", response_class=HTMLResponse)
def project_compare(project_id: str) -> HTMLResponse:
    """Open package comparison with the project's detected dependencies."""
    service = _service()
    try:
        project = service.project(project_id)
        service.track_project_workflow(project_id, "compare")
    except KeyError:
        return HTMLResponse("Project not found", status_code=404)
    candidates = [item["name"] for item in project["dependencies"]]
    return HTMLResponse(
        render_product_page(
            "decisions",
            service,
            {
                "purpose": f"Compare dependencies for {project['name']}",
                "candidates": candidates,
                "notice": f"{len(candidates)} dependencies loaded from project",
            },
        )
    )
