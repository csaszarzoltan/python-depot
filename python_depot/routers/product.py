"""HTTP contracts for PythonDepot product decision capabilities."""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from python_depot.product.decisions import DecisionWorkspaceStore
from python_depot.product.migration_planner import MigrationPlanner
from python_depot.product.policy_gate import PolicyGate, PolicyRule
from python_depot.product.portfolio import PortfolioStore
from python_depot.product.provenance import assess_provenance
from python_depot.product.trusted_reviews import ReviewModerationStore

router = APIRouter()
_STATE = Path(os.getenv("PYTHONDEPOT_PRODUCT_DB", "/tmp/python_depot_product.db"))


class WorkspaceCreate(BaseModel):
    purpose: str = Field(min_length=1, max_length=200)
    candidates: list[str] = Field(min_length=2, max_length=20)


class SnapshotCreate(BaseModel):
    dependencies: dict[str, dict]


class MigrationRequest(BaseModel):
    target_python: str
    dependencies: dict[str, dict]


class ProvenanceRequest(BaseModel):
    attestation_valid: bool | None = None
    publisher: str | None = None
    expected_publisher: str | None = None
    artifact_digest_matches: bool | None = None


class ReviewEvidenceRequest(BaseModel):
    package: str
    author: str
    body: str
    lock_hash: str


class PolicyEvaluationRequest(BaseModel):
    sbom: dict
    denied_licenses: list[str] = Field(default_factory=list)
    waivers: list[dict] = Field(default_factory=list)


def _org(x_organization_id: str | None) -> str:
    if not x_organization_id:
        raise HTTPException(status_code=401, detail="organization header required")
    return x_organization_id


@router.post("/decision-workspaces", status_code=201)
def create_workspace(body: WorkspaceCreate):
    wid = DecisionWorkspaceStore(_STATE).create(body.purpose, body.candidates)
    return {"id": wid, "state": "DRAFT", "schema_version": 1}


@router.post("/portfolios", status_code=201)
def create_portfolio(name: str, x_organization_id: str | None = Header(None)):
    organization = _org(x_organization_id)
    pid = PortfolioStore(_STATE).create(f"{organization}:{name}")
    return {"id": pid, "state": "UP_TO_DATE"}


@router.post("/portfolios/{portfolio_id}/snapshots")
def record_snapshot(portfolio_id: str, body: SnapshotCreate):
    result = PortfolioStore(_STATE).record_snapshot(portfolio_id, body.dependencies)
    return result.__dict__


@router.post("/migration-plans")
def migration_plan(body: MigrationRequest):
    return MigrationPlanner().plan(
        target_python=body.target_python, dependencies=body.dependencies
    ).__dict__


@router.post("/provenance/evaluate")
def provenance(body: ProvenanceRequest):
    return assess_provenance(**body.model_dump()).__dict__


@router.post("/trusted-reviews", status_code=201)
def trusted_review(body: ReviewEvidenceRequest):
    return ReviewModerationStore(_STATE).submit(
        body.package, body.author, body.body, evidence={"lock_hash": body.lock_hash}
    ).__dict__


@router.post("/organizations/{organization_id}/policy-evaluations")
def policy_evaluation(
    organization_id: str,
    body: PolicyEvaluationRequest,
    x_organization_id: str | None = Header(None),
):
    if _org(x_organization_id) != organization_id:
        raise HTTPException(status_code=403, detail="cross-organization access denied")
    rules = [PolicyRule(f"deny-license-{i}", "license", value) for i, value in enumerate(body.denied_licenses)]
    return PolicyGate(rules).evaluate(body.sbom, waivers=body.waivers, now=time.time()).__dict__
