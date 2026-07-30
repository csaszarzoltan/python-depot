from pathlib import Path

from python_depot.product_ui import ProductUiService, render_product_page


def service(tmp_path: Path) -> ProductUiService:
    return ProductUiService(tmp_path / "ui.db")


def test_decision_workspace_page_has_guided_shortlist(tmp_path: Path) -> None:
    html = render_product_page("decisions", service(tmp_path))
    assert "Compare packages" in html
    assert 'name="candidates"' in html
    assert "Empty state" in html


def test_trust_explainer_never_calls_identity_change_verified(tmp_path: Path) -> None:
    html = render_product_page(
        "trust",
        service(tmp_path),
        payload={"attestation_valid": True, "publisher": "fork", "expected_publisher": "origin", "artifact_digest_matches": True},
    )
    assert "Publisher changed" in html
    assert "Verified origin" not in html


def test_risk_inbox_acknowledgement_survives_refresh(tmp_path: Path) -> None:
    ui = service(tmp_path)
    item = ui.create_risk_item("project-a", "requests", "HIGH", "New vulnerability")
    ui.update_risk_item(item, "ACKNOWLEDGED")
    html = render_product_page("risk-inbox", ui)
    assert "ACKNOWLEDGED" in html and "New vulnerability" in html


def test_upgrade_planner_explains_transitive_blocker(tmp_path: Path) -> None:
    html = render_product_page("upgrade", service(tmp_path), payload={"target_python":"3.13","dependencies":{"app":{"requires_python":">=3.12","depends_on":["legacy"]},"legacy":{"requires_python":"<3.13","depends_on":[]}}})
    assert "legacy" in html and "app → legacy" in html


def test_review_center_hides_moderation_for_package_owner(tmp_path: Path) -> None:
    ui = service(tmp_path)
    ui.submit_review("demo", "alice", "Useful", "lock-1")
    html = render_product_page("reviews", ui, payload={"actor_packages":["demo"]})
    assert "Useful" in html
    assert "Hide review" not in html


def test_policy_console_marks_expired_waiver_failed(tmp_path: Path) -> None:
    html = render_product_page("policy", service(tmp_path), payload={"sbom":{"components":[{"name":"x","license":"GPL"}]},"denied_licenses":["GPL"],"waivers":[{"rule_id":"deny-license-0","expires_at":1}],"now":2})
    assert "FAIL" in html
    assert "Expired waiver" in html


def test_all_pages_have_accessible_landmarks_and_recovery(tmp_path: Path) -> None:
    for page in ("decisions", "trust", "risk-inbox", "upgrade", "reviews", "policy"):
        html = render_product_page(page, service(tmp_path))
        assert "Skip to content" in html
        assert 'aria-live="polite"' in html
        assert "Try again" in html
