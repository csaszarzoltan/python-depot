"""Acceptance tests for the v0.7 daily-workflow improvements."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from python_depot.product_ui import ProductUiService, render_product_page
from python_depot.routers import product_pages


def ui(tmp_path: Path) -> ProductUiService:
    return ProductUiService(tmp_path / "product-ui.db")


def test_risk_inbox_supports_search_state_filter_and_action(tmp_path: Path) -> None:
    service = ui(tmp_path)
    first = service.create_risk_item("checkout", "requests", "HIGH", "Fix available")
    service.create_risk_item("analytics", "pandas", "LOW", "Review update")
    filtered = render_product_page(
        "risk-inbox", service, {"query": "request", "state": "NEW"}
    )
    assert "requests" in filtered
    assert "pandas" not in filtered
    assert f'action="/workspace/risk-inbox/{first}/state"' in filtered
    assert 'name="return_query" value="request"' in filtered
    assert 'aria-label="Actions for requests"' in filtered


def test_risk_transition_records_audit_history_and_telemetry(tmp_path: Path) -> None:
    service = ui(tmp_path)
    item = service.create_risk_item("checkout", "requests", "HIGH", "Fix available")
    service.update_risk_item(item, "ACKNOWLEDGED", actor="alice", note="Investigating")
    details = service.risk_item(item)
    assert details["state"] == "ACKNOWLEDGED"
    assert details["history"][0]["actor"] == "alice"
    assert details["history"][0]["note"] == "Investigating"
    assert any(
        event["event_type"] == "risk_state_changed"
        for event in service.telemetry_events()
    )


def test_upgrade_accepts_requirements_text_and_reports_ignored_lines(
    tmp_path: Path,
) -> None:
    page = render_product_page(
        "upgrade",
        ui(tmp_path),
        {
            "target_python": "3.13",
            "dependency_input": "requests>=2.31\n# comment\n-e ./local\nlegacy; python_version < '3.13'",
        },
    )
    assert "2 dependencies detected" in page
    assert "1 line needs review" in page
    assert "Upgrade blocked" in page
    assert "legacy" in page


def test_empty_workspace_never_claims_evidence_is_current(tmp_path: Path) -> None:
    page = render_product_page("trust", ui(tmp_path))
    assert "Evidence not evaluated" in page
    assert "Evidence freshness: current" not in page


def test_decision_form_preserves_values_and_shows_validation_errors(
    tmp_path: Path,
) -> None:
    page = render_product_page(
        "decisions",
        ui(tmp_path),
        {
            "purpose": "Choose HTTP client",
            "candidates": ["httpx"],
            "errors": ["Add at least two distinct packages."],
        },
    )
    assert "Choose HTTP client" in page
    assert "httpx" in page
    assert "Add at least two distinct packages." in page
    assert 'role="alert"' in page


def test_post_risk_transition_redirects_to_preserved_filter(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "route.db"
    monkeypatch.setattr(product_pages, "_DB", db)
    service = ProductUiService(db)
    item = service.create_risk_item("checkout", "requests", "HIGH", "Fix available")
    app = FastAPI()
    app.include_router(product_pages.router)
    client = TestClient(app)
    response = client.post(
        f"/workspace/risk-inbox/{item}/state",
        data={
            "state": "ACKNOWLEDGED",
            "return_query": "request",
            "return_state": "NEW",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "?q=request&state=NEW&notice=Risk+updated"
    )
    assert ProductUiService(db).risk_item(item)["state"] == "ACKNOWLEDGED"
