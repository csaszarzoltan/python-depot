"""FastAPI page routes for the six PythonDepot product workspaces."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from python_depot.product_ui import ProductUiService, render_product_page

router = APIRouter()
_DB = Path(os.getenv("PYTHONDEPOT_PRODUCT_DB", "/tmp/python_depot_product.db"))


def _service() -> ProductUiService:
    return ProductUiService(_DB)


@router.get("/workspace/{page}", response_class=HTMLResponse)
def product_workspace(page: str, request: Request) -> HTMLResponse:
    """Render a product workspace and its empty, status, and recovery states."""
    try:
        return HTMLResponse(render_product_page(page, _service()))
    except KeyError:
        return HTMLResponse("Product workspace not found", status_code=404)


@router.post("/workspace/decisions", response_class=HTMLResponse)
def decision_workspace_submit(
    purpose: str = Form(...), candidates: str = Form(...)
) -> HTMLResponse:
    items = [item.strip() for item in candidates.split(",") if item.strip()]
    return HTMLResponse(
        render_product_page(
            "decisions", _service(), {"purpose": purpose, "candidates": items}
        )
    )


@router.post("/workspace/upgrade", response_class=HTMLResponse)
def upgrade_workspace_submit(
    target_python: str = Form(...), dependencies: str = Form(...)
) -> HTMLResponse:
    try:
        payload = json.loads(dependencies)
    except json.JSONDecodeError:
        return HTMLResponse(
            render_product_page("upgrade", _service()), status_code=422
        )
    return HTMLResponse(
        render_product_page(
            "upgrade",
            _service(),
            {"target_python": target_python, "dependencies": payload},
        )
    )
