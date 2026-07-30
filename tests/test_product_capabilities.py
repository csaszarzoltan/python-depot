from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_depot.product.decisions import DecisionWorkspaceStore
from python_depot.product.migration_planner import MigrationPlanner
from python_depot.product.policy_gate import PolicyGate, PolicyRule
from python_depot.product.portfolio import PortfolioStore
from python_depot.product.provenance import assess_provenance
from python_depot.product.trusted_reviews import ReviewModerationStore


def test_workspace_freezes_comparable_candidate_evidence(tmp_path: Path) -> None:
    store = DecisionWorkspaceStore(tmp_path / "product.db")
    wid = store.create("web framework", ["fastapi", "flask"])
    store.add_snapshot(wid, "fastapi", {"health": 91, "license": "MIT"}, observed_at=10)
    store.add_snapshot(wid, "flask", {"health": 88, "license": "BSD-3-Clause"}, observed_at=10)
    decision = store.decide(wid, "fastapi", "typed API support")
    assert decision.selected == "fastapi"
    assert decision.evidence_digest


def test_changed_trusted_publisher_is_not_verified() -> None:
    result = assess_provenance(
        attestation_valid=True,
        publisher="github:evil/fork",
        expected_publisher="github:org/project",
        artifact_digest_matches=True,
    )
    assert result.status == "IDENTITY_CHANGED"


def test_unchanged_snapshot_does_not_send_duplicate_alert(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    pid = store.create("production")
    first = store.record_snapshot(pid, {"a": {"risk": "low"}})
    second = store.record_snapshot(pid, {"a": {"risk": "low"}})
    assert first.changed is True
    assert second.changed is False
    assert store.pending_alerts(pid) == []


def test_planner_identifies_transitive_python_blocker() -> None:
    plan = MigrationPlanner().plan(
        target_python="3.13",
        dependencies={
            "app": {"requires_python": ">=3.12", "depends_on": ["legacy"]},
            "legacy": {"requires_python": "<3.13", "depends_on": []},
        },
    )
    assert plan.status == "BLOCKED"
    assert plan.blockers[0].package == "legacy"


def test_owner_cannot_moderate_competing_review(tmp_path: Path) -> None:
    store = ReviewModerationStore(tmp_path / "reviews.db")
    review = store.submit("package-a", "reviewer", "Useful", evidence={"lock_hash": "abc"})
    with pytest.raises(PermissionError):
        store.moderate(review.id, actor="package-a-owner", action="HIDE", actor_packages={"package-a"})


def test_expired_waiver_cannot_turn_denied_license_into_pass() -> None:
    gate = PolicyGate([PolicyRule("deny-license", "license", "GPL-3.0")])
    result = gate.evaluate(
        {"components": [{"name": "x", "license": "GPL-3.0"}]},
        waivers=[{"rule_id": "deny-license", "expires_at": 1}],
        now=2,
    )
    assert result.outcome == "FAIL"
    assert result.violations == ("deny-license:x",)


def test_workspace_rejects_duplicate_candidates(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DECIDE_DUPLICATE_CANDIDATE"):
        DecisionWorkspaceStore(tmp_path / "d.db").create("choice", ["x", "x"])


def test_invalid_attestation_is_invalid_even_with_same_publisher() -> None:
    assert assess_provenance(attestation_valid=False, publisher="a", expected_publisher="a", artifact_digest_matches=True).status == "INVALID"


def test_portfolio_records_only_changed_package(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    pid = store.create("prod")
    store.record_snapshot(pid, {"a": {"risk": "low"}, "b": {"risk": "low"}})
    result = store.record_snapshot(pid, {"a": {"risk": "high"}, "b": {"risk": "low"}})
    assert result.changes == ("a",)


def test_migration_plan_ready_without_blockers() -> None:
    plan = MigrationPlanner().plan(target_python="3.13", dependencies={"a": {"requires_python": ">=3.12", "depends_on": []}})
    assert plan.status == "PLAN_READY"


def test_review_requires_usage_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="REVIEW_EVIDENCE_INVALID"):
        ReviewModerationStore(tmp_path / "r.db").submit("a", "u", "text", evidence={})


def test_private_catalog_is_tenant_scoped() -> None:
    gate = PolicyGate([])
    packages = [{"name": "public"}, {"name": "private-a", "private": True, "organization_id": "a"}, {"name": "private-b", "private": True, "organization_id": "b"}]
    assert [p["name"] for p in gate.filter_private_catalog(packages, "a")] == ["public", "private-a"]
