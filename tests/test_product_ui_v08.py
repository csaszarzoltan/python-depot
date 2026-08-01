"""TDD acceptance tests for v0.8 risk ownership and bulk triage."""

from pathlib import Path

from python_depot.product_ui import ProductUiService, render_product_page


def ui(tmp_path: Path) -> ProductUiService:
    return ProductUiService(tmp_path / "v08.db")


def test_assign_risk_persists_owner_due_date_and_history(tmp_path: Path) -> None:
    service = ui(tmp_path)
    item = service.create_risk_item("api", "requests", "HIGH", "Upgrade available")
    service.update_risk_item(
        item,
        "ASSIGNED",
        actor="lead",
        note="Own remediation",
        owner="alice",
        due_date="2026-08-15",
    )
    risk = service.risk_item(item)
    assert risk["owner"] == "alice"
    assert risk["due_date"] == "2026-08-15"
    assert risk["history"][0]["to_state"] == "ASSIGNED"


def test_bulk_update_is_transactional_and_audited(tmp_path: Path) -> None:
    service = ui(tmp_path)
    first = service.create_risk_item("api", "a", "HIGH", "A")
    second = service.create_risk_item("api", "b", "MEDIUM", "B")
    result = service.bulk_update_risk_items(
        [first, second], "ACKNOWLEDGED", actor="secops", note="Daily triage"
    )
    assert result == {"updated": 2, "failed": []}
    assert {x["state"] for x in service.risk_items()} == {"ACKNOWLEDGED"}
    assert len(service.risk_item(first)["history"]) == 1


def test_bulk_update_rejects_unknown_item_without_partial_commit(
    tmp_path: Path,
) -> None:
    service = ui(tmp_path)
    item = service.create_risk_item("api", "a", "HIGH", "A")
    try:
        service.bulk_update_risk_items([item, "missing"], "RESOLVED")
    except KeyError:
        pass
    else:
        raise AssertionError("missing item must fail")
    assert service.risk_item(item)["state"] == "NEW"


def test_inbox_exposes_selection_owner_due_date_and_detail_link(tmp_path: Path) -> None:
    service = ui(tmp_path)
    item = service.create_risk_item("api", "requests", "HIGH", "Upgrade available")
    service.update_risk_item(item, "ASSIGNED", owner="alice", due_date="2026-08-15")
    page = render_product_page("risk-inbox", service)
    assert 'name="item_ids"' in page
    assert "alice" in page
    assert "2026-08-15" in page
    assert f"/workspace/risk-inbox/{item}" in page
    assert 'action="/workspace/risk-inbox/bulk"' in page


def test_risk_detail_renders_history_and_context(tmp_path: Path) -> None:
    service = ui(tmp_path)
    item = service.create_risk_item("api", "requests", "HIGH", "Upgrade available")
    service.update_risk_item(item, "ACKNOWLEDGED", actor="alice", note="Checking fix")
    page = render_product_page("risk-detail", service, {"item_id": item})
    assert "Upgrade available" in page
    assert "Checking fix" in page
    assert "ACKNOWLEDGED" in page
    assert "Back to risk inbox" in page
