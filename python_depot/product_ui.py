"""Accessible server-rendered product workspaces for PythonDepot.

This module is deliberately independent from FastAPI and SQLAlchemy. It provides
view models, persistence for UI-only workflow state, and deterministic HTML so
that the six product experiences can be tested without external services.
"""
from __future__ import annotations

import html
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from python_depot.product.migration_planner import MigrationPlanner
from python_depot.product.policy_gate import PolicyGate, PolicyRule
from python_depot.product.provenance import assess_provenance


_PAGES = {
    "decisions": ("Compare packages", "Build a shortlist and record a defensible choice."),
    "trust": ("Package trust", "Understand origin evidence without confusing provenance with safety."),
    "risk-inbox": ("Risk inbox", "Triage package changes by severity, owner, and workflow state."),
    "upgrade": ("Python upgrade planner", "Find direct and transitive blockers before changing Python."),
    "reviews": ("Trusted reviews", "Share evidence-backed experience and moderate transparently."),
    "policy": ("SBOM policy console", "Evaluate policy, inspect violations, and review expiring waivers."),
}


class ProductUiService:
    """Persist UI workflow state in an isolated SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS risk_items(
                    id TEXT PRIMARY KEY, project TEXT, package TEXT, severity TEXT,
                    message TEXT, state TEXT, updated_at REAL
                );
                CREATE TABLE IF NOT EXISTS ui_reviews(
                    id TEXT PRIMARY KEY, package TEXT, author TEXT, body TEXT,
                    evidence_hash TEXT, state TEXT
                );
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def create_risk_item(self, project: str, package: str, severity: str, message: str) -> str:
        item_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute(
                "INSERT INTO risk_items VALUES (?,?,?,?,?,'NEW',?)",
                (item_id, project, package, severity, message, time.time()),
            )
        return item_id

    def update_risk_item(self, item_id: str, state: str) -> None:
        allowed = {"ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "RESOLVED", "REOPENED"}
        if state not in allowed:
            raise ValueError("INBOX_INVALID_TRANSITION")
        with self._db() as db:
            cursor = db.execute(
                "UPDATE risk_items SET state=?, updated_at=? WHERE id=?",
                (state, time.time(), item_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)

    def risk_items(self) -> list[dict[str, Any]]:
        with self._db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM risk_items ORDER BY updated_at DESC")]

    def submit_review(self, package: str, author: str, body: str, evidence_hash: str) -> str:
        if not all(value.strip() for value in (package, author, body, evidence_hash)):
            raise ValueError("REVIEW_EVIDENCE_INVALID")
        review_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute(
                "INSERT INTO ui_reviews VALUES (?,?,?,?,?,'VERIFIED_USER')",
                (review_id, package, author, body, evidence_hash),
            )
        return review_id

    def reviews(self) -> list[dict[str, Any]]:
        with self._db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM ui_reviews ORDER BY rowid DESC")]


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _layout(page: str, content: str, notice: str = "Ready") -> str:
    title, subtitle = _PAGES[page]
    nav = "".join(
        f'<a href="/workspace/{slug}"{ " aria-current=page" if slug == page else ""}>{_esc(label)}</a>'
        for slug, (label, _subtitle) in _PAGES.items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} | PythonDepot</title><link rel="stylesheet" href="/static/css/product.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<header class="topbar"><a class="brand" href="/dashboard">PythonDepot</a><span>Decision &amp; Governance</span></header>
<div class="app-shell"><nav class="product-nav" aria-label="Product workspaces">{nav}</nav>
<main id="main" tabindex="-1"><div class="page-heading"><div><p class="eyebrow">Product workspace</p><h1>{_esc(title)}</h1><p>{_esc(subtitle)}</p></div><span class="freshness">Evidence freshness: current</span></div>
<div class="status" aria-live="polite">{_esc(notice)}</div>{content}
<section class="recovery" aria-labelledby="recovery-title"><h2 id="recovery-title">Need to recover?</h2><p>Your last stable state is preserved when an update fails.</p><button type="button">Try again</button></section>
</main></div></body></html>"""


def render_product_page(page: str, service: ProductUiService, payload: dict[str, Any] | None = None) -> str:
    """Render one of the six product workspaces from deterministic input."""
    if page not in _PAGES:
        raise KeyError(page)
    payload = payload or {}
    renderers = {
        "decisions": _decisions,
        "trust": _trust,
        "risk-inbox": _risk_inbox,
        "upgrade": _upgrade,
        "reviews": _reviews,
        "policy": _policy,
    }
    return _layout(page, renderers[page](service, payload))


def _decisions(_service: ProductUiService, payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    rows = "".join(f"<li><strong>{_esc(item)}</strong><span>Evidence pending</span></li>" for item in candidates)
    empty = '<div class="empty"><strong>Empty state</strong><p>Add at least two packages to start a comparable shortlist.</p></div>' if not rows else f"<ul class=cards>{rows}</ul>"
    return f"""<section class="panel"><h2>Build a shortlist</h2><form method="post" action="/workspace/decisions" class="stack">
<label>Decision purpose<input name="purpose" required maxlength="200" placeholder="Choose a web framework"></label>
<label>Package candidates<textarea name="candidates" required placeholder="fastapi, flask"></textarea></label>
<button class="primary">Compare packages</button></form>{empty}</section>
<section class="panel"><h2>Comparison matrix</h2><p>Health, license, provenance, maintenance, and evidence age appear in aligned columns.</p></section>"""


def _trust(_service: ProductUiService, payload: dict[str, Any]) -> str:
    if payload:
        result = assess_provenance(**payload)
        labels = {"VERIFIED": "Verified origin", "IDENTITY_CHANGED": "Publisher changed", "INVALID": "Invalid evidence", "UNATTESTED": "No attestation", "UNKNOWN": "Evidence unavailable"}
        label = labels[result.status]
        reasons = "".join(f"<li>{_esc(reason)}</li>" for reason in result.reasons) or "<li>No contradiction found in supplied origin evidence.</li>"
        card = f'<div class="trust-card state-{result.status.lower()}"><h2>{label}</h2><p>Publisher: {_esc(result.publisher or "Not available")}</p><ul>{reasons}</ul></div>'
    else:
        card = '<div class="empty"><h2>No release selected</h2><p>Choose a package version to inspect provenance, publisher identity, and artifact digest evidence.</p></div>'
    return card + '<section class="panel"><h2>What this means</h2><p>Origin evidence proves where an artifact came from. It does not prove that the code is safe.</p><details><summary>View release evidence</summary><p>Attestation, publisher, digest, source, and observation time are presented here.</p></details></section>'


def _risk_inbox(service: ProductUiService, payload: dict[str, Any]) -> str:
    items = service.risk_items()
    if not items:
        body = '<div class="empty"><h2>No risk changes</h2><p>Import or refresh a portfolio to create a risk-delta inbox.</p></div>'
    else:
        rows = "".join(f'<tr><td>{_esc(x["project"])}</td><td>{_esc(x["package"])}</td><td><span class="severity">{_esc(x["severity"])}</span></td><td>{_esc(x["message"])}</td><td>{_esc(x["state"])}</td></tr>' for x in items)
        body = f'<div class="filters"><label>State<select><option>All states</option><option>NEW</option><option>ACKNOWLEDGED</option></select></label><label>Search<input type=search placeholder="Package or project"></label></div><table><thead><tr><th>Project</th><th>Package</th><th>Severity</th><th>Change</th><th>State</th></tr></thead><tbody>{rows}</tbody></table>'
    return f'<section class="panel"><div class="section-heading"><h2>Risk changes</h2><button class=primary>Refresh portfolio</button></div>{body}</section>'


def _upgrade(_service: ProductUiService, payload: dict[str, Any]) -> str:
    result = None
    if payload.get("dependencies"):
        result = MigrationPlanner().plan(target_python=payload["target_python"], dependencies=payload["dependencies"])
    if result and result.blockers:
        blockers = "".join(f'<li><strong>{_esc(b.package)}</strong><span>{_esc(" → ".join(b.path))}</span><small>{_esc(b.constraint)}</small></li>' for b in result.blockers)
        output = f'<div class="callout warning"><h2>Upgrade blocked</h2><ul class=cards>{blockers}</ul></div>'
    elif result:
        output = '<div class="callout success"><h2>Plan ready</h2><p>No declared Python-version blocker was found. Run the validation checklist next.</p></div>'
    else:
        output = '<div class="empty"><h2>Import a project</h2><p>Paste dependency metadata or upload a supported lockfile to map blockers.</p></div>'
    return f'<section class="panel"><ol class=steps><li class=active>Import</li><li>Analyze</li><li>Plan</li><li>Validate</li></ol><form class="stack"><label>Target Python<select name=target_python><option>3.13</option><option>3.12</option></select></label><label>Dependency data<textarea name=dependencies placeholder="Project dependency JSON"></textarea></label><button class=primary>Analyze compatibility</button></form>{output}</section>'


def _reviews(service: ProductUiService, payload: dict[str, Any]) -> str:
    actor_packages = set(payload.get("actor_packages", []))
    reviews = service.reviews()
    cards = []
    for review in reviews:
        moderation = "" if review["package"] in actor_packages else '<button type=button>Hide review</button>'
        cards.append(f'<article class="review"><h2>{_esc(review["package"])}</h2><p>{_esc(review["body"])}</p><span>{_esc(review["state"])}</span>{moderation}</article>')
    listing = "".join(cards) or '<div class="empty"><h2>No verified reviews</h2><p>Be the first to share evidence-backed package experience.</p></div>'
    return f'<section class="panel"><h2>Write a verified review</h2><form class=stack><label>Package<input name=package required></label><label>Experience<textarea name=body required></textarea></label><label>Lock evidence hash<input name=lock_hash required></label><p class=privacy>Only the evidence hash is published; local paths and dependency contents remain private.</p><button class=primary>Preview review</button></form></section><section class=panel><h2>Review center</h2>{listing}</section>'


def _policy(_service: ProductUiService, payload: dict[str, Any]) -> str:
    if payload.get("sbom"):
        rules = [PolicyRule(f"deny-license-{i}", "license", value) for i, value in enumerate(payload.get("denied_licenses", []))]
        now = float(payload.get("now", time.time()))
        result = PolicyGate(rules).evaluate(payload["sbom"], waivers=payload.get("waivers", []), now=now)
        expired = any(float(w.get("expires_at", 0)) < now for w in payload.get("waivers", []))
        violations = "".join(f"<li>{_esc(v)}</li>" for v in result.violations) or "<li>No active violations</li>"
        expiry = '<div class="callout danger"><strong>Expired waiver</strong><p>Expired exceptions do not change the policy outcome.</p></div>' if expired else ""
        outcome = f'<div class="outcome {result.outcome.lower()}"><h2>{_esc(result.outcome)}</h2><ul>{violations}</ul></div>{expiry}'
    else:
        outcome = '<div class="empty"><h2>No evaluation yet</h2><p>Upload an SBOM or use dry-run to test a draft policy.</p></div>'
    return f'<section class="panel"><div class="section-heading"><h2>Organization policy</h2><button class=primary>New policy rule</button></div><div class=two-column><div><h3>Visual rule editor</h3><label>Denied license<input placeholder="GPL-3.0"></label><button>Run dry-run</button></div><div><h3>Evaluation</h3>{outcome}</div></div></section><section class=panel><h2>Waiver approval queue</h2><p>Requests show owner, justification, expiration, affected components, and audit history.</p></section>'
