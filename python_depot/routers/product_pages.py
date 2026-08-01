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
) -> RedirectResponse:
    """Update one risk and return to the user's filtered inbox."""
    try:
        _service().update_risk_item(item_id, state)
        notice = "Risk updated"
    except (KeyError, ValueError):
        notice = "Risk update failed"
    query = urlencode({"q": return_query, "state": return_state, "notice": notice})
    return RedirectResponse(f"/workspace/risk-inbox?{query}", status_code=303)
