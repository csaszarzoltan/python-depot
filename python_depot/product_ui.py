"""Accessible server-rendered product workspaces for PythonDepot.

This module is deliberately independent from FastAPI and SQLAlchemy. It provides
view models, persistence for UI-only workflow state, and deterministic HTML so
that the six product experiences can be tested without external services.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from python_depot.product.migration_planner import MigrationPlanner
from python_depot.product.policy_gate import PolicyGate, PolicyRule
from python_depot.product.provenance import assess_provenance

_PAGES = {
    "projects": (
        "Projects",
        "Save dependency context once and reuse it across daily workflows.",
    ),
    "project-detail": (
        "Project workspace",
        "Review the current dependency snapshot and changes over time.",
    ),
    "decisions": (
        "Compare packages",
        "Build a shortlist and record a defensible choice.",
    ),
    "trust": (
        "Package trust",
        "Understand origin evidence without confusing provenance with safety.",
    ),
    "risk-inbox": (
        "Risk inbox",
        "Triage package changes by severity, owner, and workflow state.",
    ),
    "risk-detail": (
        "Risk detail",
        "Review context, ownership, and the complete activity history.",
    ),
    "upgrade": (
        "Python upgrade planner",
        "Find direct and transitive blockers before changing Python.",
    ),
    "reviews": (
        "Trusted reviews",
        "Share evidence-backed experience and moderate transparently.",
    ),
    "policy": (
        "SBOM policy console",
        "Evaluate policy, inspect violations, and review expiring waivers.",
    ),
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
                CREATE TABLE IF NOT EXISTS risk_history(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, actor TEXT,
                    from_state TEXT, to_state TEXT, note TEXT, created_at REAL
                );
                CREATE TABLE IF NOT EXISTS telemetry_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT,
                    properties TEXT, created_at REAL
                );
                CREATE TABLE IF NOT EXISTS projects(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_snapshots(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
                    dependencies TEXT NOT NULL, raw_input TEXT NOT NULL,
                    ignored_lines INTEGER NOT NULL, created_at REAL NOT NULL
                );
                """
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(risk_items)")}
            if "owner" not in columns:
                db.execute(
                    "ALTER TABLE risk_items ADD COLUMN owner TEXT NOT NULL DEFAULT ''"
                )
            if "due_date" not in columns:
                db.execute(
                    "ALTER TABLE risk_items ADD COLUMN due_date TEXT NOT NULL DEFAULT ''"
                )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def create_risk_item(
        self, project: str, package: str, severity: str, message: str
    ) -> str:
        item_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute(
                "INSERT INTO risk_items(id,project,package,severity,message,state,updated_at,owner,due_date) VALUES (?,?,?,?,?,'NEW',?,'','')",
                (item_id, project, package, severity, message, time.time()),
            )
        return item_id

    def update_risk_item(
        self,
        item_id: str,
        state: str,
        *,
        actor: str = "local-user",
        note: str = "",
        owner: str | None = None,
        due_date: str | None = None,
    ) -> None:
        allowed = {"ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "RESOLVED", "REOPENED"}
        if state not in allowed:
            raise ValueError("INBOX_INVALID_TRANSITION")
        now = time.time()
        with self._db() as db:
            current = db.execute(
                "SELECT state FROM risk_items WHERE id=?", (item_id,)
            ).fetchone()
            if current is None:
                raise KeyError(item_id)
            db.execute(
                "UPDATE risk_items SET state=?, updated_at=?, owner=COALESCE(?,owner), due_date=COALESCE(?,due_date) WHERE id=?",
                (state, now, owner, due_date, item_id),
            )
            db.execute(
                "INSERT INTO risk_history(item_id,actor,from_state,to_state,note,created_at) VALUES (?,?,?,?,?,?)",
                (
                    item_id,
                    actor.strip() or "local-user",
                    current[0],
                    state,
                    note.strip(),
                    now,
                ),
            )
            self._track(
                db,
                "risk_state_changed",
                {"item_id": item_id, "from": current[0], "to": state},
            )

    def bulk_update_risk_items(
        self,
        item_ids: list[str],
        state: str,
        *,
        actor: str = "local-user",
        note: str = "",
    ) -> dict[str, Any]:
        """Atomically transition selected risk items and audit every change."""
        allowed = {"ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "RESOLVED", "REOPENED"}
        cleaned = list(dict.fromkeys(x for x in item_ids if x))
        if state not in allowed or not cleaned:
            raise ValueError("INBOX_INVALID_BULK_UPDATE")
        now = time.time()
        with self._db() as db:
            placeholders = ",".join("?" for _ in cleaned)
            rows = db.execute(
                f"SELECT id,state FROM risk_items WHERE id IN ({placeholders})", cleaned
            ).fetchall()
            current = {row[0]: row[1] for row in rows}
            missing = [item_id for item_id in cleaned if item_id not in current]
            if missing:
                raise KeyError(missing[0])
            for item_id in cleaned:
                db.execute(
                    "UPDATE risk_items SET state=?,updated_at=? WHERE id=?",
                    (state, now, item_id),
                )
                db.execute(
                    "INSERT INTO risk_history(item_id,actor,from_state,to_state,note,created_at) VALUES (?,?,?,?,?,?)",
                    (item_id, actor, current[item_id], state, note.strip(), now),
                )
            self._track(
                db, "risk_bulk_state_changed", {"count": len(cleaned), "to": state}
            )
        return {"updated": len(cleaned), "failed": []}

    @staticmethod
    def _track(
        db: sqlite3.Connection, event_type: str, properties: dict[str, Any]
    ) -> None:
        """Store privacy-conscious product telemetry without dependency contents."""
        db.execute(
            "INSERT INTO telemetry_events(event_type,properties,created_at) VALUES (?,?,?)",
            (event_type, json.dumps(properties, sort_keys=True), time.time()),
        )

    def risk_items(self, *, query: str = "", state: str = "") -> list[dict[str, Any]]:
        sql = "SELECT * FROM risk_items WHERE 1=1"
        params: list[Any] = []
        if query.strip():
            sql += " AND (lower(project) LIKE ? OR lower(package) LIKE ? OR lower(message) LIKE ?)"
            needle = f"%{query.strip().lower()}%"
            params.extend([needle, needle, needle])
        if state and state != "ALL":
            sql += " AND state=?"
            params.append(state)
        sql += " ORDER BY updated_at DESC"
        with self._db() as db:
            return [dict(row) for row in db.execute(sql, params)]

    def risk_item(self, item_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM risk_items WHERE id=?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(item_id)
            result = dict(row)
            result["history"] = [
                dict(x)
                for x in db.execute(
                    "SELECT actor,from_state,to_state,note,created_at FROM risk_history WHERE item_id=? ORDER BY id DESC",
                    (item_id,),
                )
            ]
            return result

    def telemetry_events(self) -> list[dict[str, Any]]:
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT event_type,properties,created_at FROM telemetry_events ORDER BY id"
                )
            ]

    def create_project(self, name: str, source: str, dependencies: str) -> str:
        """Create a durable project and its first dependency snapshot."""
        if not name.strip() or not source.strip():
            raise ValueError("PROJECT_REQUIRED_FIELDS")
        project_id = uuid.uuid4().hex
        now = time.time()
        with self._db() as db:
            db.execute(
                "INSERT INTO projects VALUES (?,?,?,?,?)",
                (project_id, name.strip(), source.strip(), now, now),
            )
        self.import_project_dependencies(project_id, dependencies)
        return project_id

    @staticmethod
    def _dependency_rows(raw: str) -> tuple[list[dict[str, str]], int]:
        parsed, ignored = _parse_dependency_input(raw)
        rows = []
        for name in sorted(parsed):
            match = re.search(
                rf"(?im)^\s*{re.escape(name)}(?:\[[^]]+\])?\s*([^;#\s]+)?", raw
            )
            constraint = (match.group(1) or "") if match else ""
            rows.append({"name": name, "constraint": constraint})
        return rows, ignored

    def import_project_dependencies(self, project_id: str, raw: str) -> dict[str, Any]:
        """Append a snapshot and return package-level changes from the previous one."""
        rows, ignored = self._dependency_rows(raw)
        now = time.time()
        with self._db() as db:
            project = db.execute(
                "SELECT id FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            if project is None:
                raise KeyError(project_id)
            previous = db.execute(
                "SELECT dependencies FROM project_snapshots WHERE project_id=? ORDER BY id DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            old = (
                {x["name"]: x.get("constraint", "") for x in json.loads(previous[0])}
                if previous
                else {}
            )
            new = {x["name"]: x.get("constraint", "") for x in rows}
            db.execute(
                "INSERT INTO project_snapshots(project_id,dependencies,raw_input,ignored_lines,created_at) VALUES (?,?,?,?,?)",
                (project_id, json.dumps(rows, sort_keys=True), raw, ignored, now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
            self._track(
                db,
                "project_snapshot_imported",
                {"project_id": project_id, "count": len(rows)},
            )
        return {
            "added": sorted(set(new) - set(old)),
            "removed": sorted(set(old) - set(new)),
            "changed": sorted(
                name for name in set(old) & set(new) if old[name] != new[name]
            ),
            "ignored_lines": ignored,
        }

    def track_project_workflow(self, project_id: str, workflow: str) -> None:
        """Record a privacy-safe launch from a saved project into another workflow."""
        allowed = {"upgrade", "compare", "risks"}
        if workflow not in allowed:
            raise ValueError("PROJECT_WORKFLOW_INVALID")
        with self._db() as db:
            exists = db.execute(
                "SELECT 1 FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(project_id)
            self._track(
                db,
                "project_workflow_opened",
                {"project_id": project_id, "workflow": workflow},
            )

    def projects(self) -> list[dict[str, Any]]:
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT p.*, (SELECT COUNT(*) FROM project_snapshots s WHERE s.project_id=p.id) snapshot_count FROM projects p ORDER BY updated_at DESC"
                )
            ]

    def project(self, project_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            if row is None:
                raise KeyError(project_id)
            result = dict(row)
            snapshots = [
                dict(x)
                for x in db.execute(
                    "SELECT id,dependencies,raw_input,ignored_lines,created_at FROM project_snapshots WHERE project_id=? ORDER BY id DESC",
                    (project_id,),
                )
            ]
            for snapshot in snapshots:
                snapshot["dependencies"] = json.loads(snapshot["dependencies"])
            result["snapshots"] = snapshots
            latest = (
                snapshots[0]
                if snapshots
                else {"dependencies": [], "ignored_lines": 0, "raw_input": ""}
            )
            result["dependencies"] = latest["dependencies"]
            result["ignored_lines"] = latest["ignored_lines"]
            result["raw_input"] = latest["raw_input"]
            return result

    def submit_review(
        self, package: str, author: str, body: str, evidence_hash: str
    ) -> str:
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
            return [
                dict(row)
                for row in db.execute("SELECT * FROM ui_reviews ORDER BY rowid DESC")
            ]


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _layout(
    page: str, content: str, notice: str = "Ready", has_evidence: bool = False
) -> str:
    title, subtitle = _PAGES[page]
    nav = "".join(
        f'<a href="/workspace/{slug}"{" aria-current=page" if slug == page else ""}>{_esc(label)}</a>'
        for slug, (label, _subtitle) in _PAGES.items()
        if slug not in {"risk-detail", "project-detail"}
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} | PythonDepot</title><link rel="stylesheet" href="/static/css/product.css"></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<header class="topbar"><a class="brand" href="/dashboard">PythonDepot</a><span>Decision &amp; Governance</span></header>
<div class="app-shell"><nav class="product-nav" aria-label="Product workspaces">{nav}</nav>
<main id="main" tabindex="-1"><div class="page-heading"><div><p class="eyebrow">Product workspace</p><h1>{_esc(title)}</h1><p>{_esc(subtitle)}</p></div><span class="freshness">{"Current evidence snapshot" if has_evidence else "Evidence not evaluated"}</span></div>
<div class="status" aria-live="polite">{_esc(notice)}</div>{content}
<section class="recovery" aria-labelledby="recovery-title"><h2 id="recovery-title">Need to recover?</h2><p>Your last stable state is preserved when an update fails.</p><button type="button">Try again</button></section>
</main></div></body></html>"""


def render_product_page(
    page: str, service: ProductUiService, payload: dict[str, Any] | None = None
) -> str:
    """Render one of the six product workspaces from deterministic input."""
    if page not in _PAGES:
        raise KeyError(page)
    payload = payload or {}
    renderers = {
        "projects": _projects,
        "project-detail": _project_detail,
        "decisions": _decisions,
        "trust": _trust,
        "risk-inbox": _risk_inbox,
        "risk-detail": _risk_detail,
        "upgrade": _upgrade,
        "reviews": _reviews,
        "policy": _policy,
    }
    notice = str(payload.get("notice", "Ready"))
    has_evidence = bool(payload) and not bool(payload.get("errors"))
    return _layout(page, renderers[page](service, payload), notice, has_evidence)


def _projects(service: ProductUiService, _payload: dict[str, Any]) -> str:
    projects = service.projects()
    if projects:
        listing = "".join(
            f'<li><a href="/workspace/projects/{_esc(item["id"])}"><strong>{_esc(item["name"])}</strong></a><span>{_esc(item["source"])}</span><small>{item["snapshot_count"]} snapshots</small></li>'
            for item in projects
        )
        body = f'<ul class="cards project-list">{listing}</ul>'
    else:
        body = '<div class="empty"><h2>No projects yet</h2><p>Create a project once to reuse its dependency context across upgrade, policy, and risk workflows.</p></div>'
    return f'<section class="panel"><h2>Saved projects</h2>{body}</section><section class="panel"><h2>Create project</h2><form method="post" action="/workspace/projects" class="stack"><label>Project name<input name="name" required maxlength="120" placeholder="Checkout API"></label><label>Repository or source<input name="source" required maxlength="300" placeholder="team/checkout"></label><label>Dependencies<textarea name="dependencies" required placeholder="requests>=2.31"></textarea></label><button class="primary">Create project</button></form></section>'


def _project_detail(service: ProductUiService, payload: dict[str, Any]) -> str:
    project = service.project(str(payload["project_id"]))
    dependencies = (
        "".join(
            f"<tr><td>{_esc(item['name'])}</td><td>{_esc(item.get('constraint') or 'Unpinned')}</td></tr>"
            for item in project["dependencies"]
        )
        or '<tr><td colspan="2">No dependencies detected</td></tr>'
    )
    history = "".join(
        f"<li><strong>Snapshot {len(project['snapshots']) - index}</strong><span>{len(snapshot['dependencies'])} dependencies; {snapshot['ignored_lines']} lines need review</span></li>"
        for index, snapshot in enumerate(project["snapshots"])
    )
    notice = str(payload.get("change_notice", ""))
    callout = (
        f'<div class="callout success" role="status">{_esc(notice)}</div>'
        if notice
        else ""
    )
    project_query = quote_plus(str(project["name"]))
    actions = f'<nav class="context-actions" aria-label="Project actions"><a class="button primary" href="/workspace/projects/{_esc(project["id"])}/upgrade">Analyze Python upgrade</a><a class="button" href="/workspace/projects/{_esc(project["id"])}/compare">Compare dependencies</a><a class="button" href="/workspace/risk-inbox?q={project_query}">View project risks</a></nav>'
    return f'<p><a href="/workspace/projects">Back to projects</a></p>{actions}<section class="panel"><h2>{_esc(project["name"])}</h2><p>{_esc(project["source"])}</p>{callout}<div class="table-wrap" tabindex="0"><table><caption>{len(project["dependencies"])} dependencies</caption><thead><tr><th>Package</th><th>Constraint</th></tr></thead><tbody>{dependencies}</tbody></table></div></section><section class="panel"><h2>Import a new snapshot</h2><form method="post" action="/workspace/projects/{_esc(project["id"])}/import" class="stack"><label>Dependency data<textarea name="dependencies" required>{_esc(project["raw_input"])}</textarea></label><button class="primary">Analyze and import</button></form></section><section class="panel"><h2>Snapshot history</h2><ol class="timeline">{history}</ol></section>'


def _decisions(_service: ProductUiService, payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    purpose = str(payload.get("purpose", ""))
    errors = payload.get("errors", [])
    rows = "".join(
        f"<li><strong>{_esc(item)}</strong><span>Evidence pending</span></li>"
        for item in candidates
    )
    error_html = ""
    if errors:
        error_html = (
            '<div class="callout danger" role="alert"><h2>Check the form</h2><ul>'
            + "".join(f"<li>{_esc(e)}</li>" for e in errors)
            + "</ul></div>"
        )
    empty = (
        '<div class="empty"><strong>Empty state</strong><p>Add at least two packages to start a comparable shortlist.</p></div>'
        if not rows
        else f"<ul class=cards>{rows}</ul>"
    )
    candidate_value = ", ".join(str(x) for x in candidates)
    return f"""<section class="panel"><h2>Build a shortlist</h2>{error_html}<form method="post" action="/workspace/decisions" class="stack">
<label>Decision purpose<input name="purpose" required maxlength="200" value="{_esc(purpose)}" placeholder="Choose a web framework"></label>
<label>Package candidates<textarea name="candidates" required aria-describedby="candidate-help" placeholder="fastapi, flask">{_esc(candidate_value)}</textarea></label>
<p id="candidate-help" class="hint">Enter at least two distinct package names separated by commas.</p>
<button class="primary">Compare packages</button></form>{empty}</section>
<section class="panel"><h2>Comparison matrix</h2><p>Health, license, provenance, maintenance, and evidence age appear in aligned columns.</p></section>"""


def _trust(_service: ProductUiService, payload: dict[str, Any]) -> str:
    if payload:
        result = assess_provenance(**payload)
        labels = {
            "VERIFIED": "Verified origin",
            "IDENTITY_CHANGED": "Publisher changed",
            "INVALID": "Invalid evidence",
            "UNATTESTED": "No attestation",
            "UNKNOWN": "Evidence unavailable",
        }
        label = labels[result.status]
        reasons = (
            "".join(f"<li>{_esc(reason)}</li>" for reason in result.reasons)
            or "<li>No contradiction found in supplied origin evidence.</li>"
        )
        card = f'<div class="trust-card state-{result.status.lower()}"><h2>{label}</h2><p>Publisher: {_esc(result.publisher or "Not available")}</p><ul>{reasons}</ul></div>'
    else:
        card = '<div class="empty"><h2>No release selected</h2><p>Choose a package version to inspect provenance, publisher identity, and artifact digest evidence.</p></div>'
    return (
        card
        + '<section class="panel"><h2>What this means</h2><p>Origin evidence proves where an artifact came from. It does not prove that the code is safe.</p><details><summary>View release evidence</summary><p>Attestation, publisher, digest, source, and observation time are presented here.</p></details></section>'
    )


def _risk_inbox(service: ProductUiService, payload: dict[str, Any]) -> str:
    query = str(payload.get("query", ""))
    state = str(payload.get("state", "ALL"))
    items = service.risk_items(query=query, state=state)
    states = [
        "ALL",
        "NEW",
        "ACKNOWLEDGED",
        "ASSIGNED",
        "SNOOZED",
        "RESOLVED",
        "REOPENED",
    ]
    options = "".join(
        f'<option value="{x}"{" selected" if x == state else ""}>{x.replace("_", " ").title()}</option>'
        for x in states
    )
    if not items:
        body = '<div class="empty"><h2>No matching risk changes</h2><p>Clear filters or refresh a portfolio to see risk deltas.</p></div>'
    else:
        rows = "".join(
            f'<tr><td><input type="checkbox" name="item_ids" value="{_esc(x["id"])}" aria-label="Select {_esc(x["package"])}"></td><td>{_esc(x["project"])}</td><td><a href="/workspace/risk-inbox/{_esc(x["id"])}">{_esc(x["package"])}</a></td><td><span class="severity">{_esc(x["severity"])}</span></td><td>{_esc(x["message"])}</td><td>{_esc(x["state"])}</td><td>{_esc(x.get("owner") or "Unassigned")}</td><td>{_esc(x.get("due_date") or "No due date")}</td><td><form method="post" action="/workspace/risk-inbox/{_esc(x["id"])}/state" aria-label="Actions for {_esc(x["package"])}" class="inline-action"><input type="hidden" name="return_query" value="{_esc(query)}"><input type="hidden" name="return_state" value="{_esc(state)}"><select name="state" aria-label="New state for {_esc(x["package"])}"><option>ACKNOWLEDGED</option><option>ASSIGNED</option><option>SNOOZED</option><option>RESOLVED</option><option>REOPENED</option></select><button>Update</button></form></td></tr>'
            for x in items
        )
        body = f'<form method="post" action="/workspace/risk-inbox/bulk"><input type="hidden" name="return_query" value="{_esc(query)}"><input type="hidden" name="return_state" value="{_esc(state)}"><div class="bulk-bar"><label>Selected action<select name="state"><option>ACKNOWLEDGED</option><option>ASSIGNED</option><option>SNOOZED</option><option>RESOLVED</option><option>REOPENED</option></select></label><label>Note<input name="note" maxlength="300" placeholder="Reason or context"></label><button>Update selected</button></div><div class="table-wrap" tabindex="0"><table><caption>{len(items)} risk items</caption><thead><tr><th scope="col">Select</th><th>Project</th><th>Package</th><th>Severity</th><th>Change</th><th>State</th><th>Owner</th><th>Due</th><th>Quick action</th></tr></thead><tbody>{rows}</tbody></table></div></form>'
    return f'<section class="panel"><div class="section-heading"><h2>Risk changes</h2><a class="button primary" href="/workspace/risk-inbox?notice=Portfolio+refresh+requested">Refresh portfolio</a></div><form method="get" class="filters" aria-label="Risk filters"><label>State<select name="state">{options}</select></label><label>Search<input name="q" type="search" value="{_esc(query)}" placeholder="Package, project, or message"></label><button>Apply filters</button><a class="button" href="/workspace/risk-inbox">Clear</a></form>{body}</section>'


def _risk_detail(service: ProductUiService, payload: dict[str, Any]) -> str:
    risk = service.risk_item(str(payload["item_id"]))
    history = (
        "".join(
            f"<li><strong>{_esc(row['to_state'])}</strong><span>by {_esc(row['actor'])} from {_esc(row['from_state'])}</span><p>{_esc(row['note'] or 'No note')}</p></li>"
            for row in risk["history"]
        )
        or "<li>No activity yet.</li>"
    )
    return f'<p><a href="/workspace/risk-inbox">Back to risk inbox</a></p><section class="panel"><h2>{_esc(risk["package"])}</h2><dl class="detail-grid"><dt>Project</dt><dd>{_esc(risk["project"])}</dd><dt>Severity</dt><dd>{_esc(risk["severity"])}</dd><dt>State</dt><dd>{_esc(risk["state"])}</dd><dt>Owner</dt><dd>{_esc(risk.get("owner") or "Unassigned")}</dd><dt>Due date</dt><dd>{_esc(risk.get("due_date") or "Not set")}</dd></dl><h3>Risk context</h3><p>{_esc(risk["message"])}</p><h3>Update risk</h3><form method="post" action="/workspace/risk-inbox/{_esc(risk["id"])}/state" class="stack"><input type="hidden" name="return_state" value="ALL"><label>State<select name="state"><option>ACKNOWLEDGED</option><option>ASSIGNED</option><option>SNOOZED</option><option>RESOLVED</option><option>REOPENED</option></select></label><label>Owner<input name="owner" value="{_esc(risk.get("owner") or "")}" maxlength="100"></label><label>Due date<input type="date" name="due_date" value="{_esc(risk.get("due_date") or "")}"></label><label>Activity note<textarea name="note" maxlength="300"></textarea></label><button class="primary">Save risk update</button></form></section><section class="panel"><h2>Activity history</h2><ol class="timeline">{history}</ol></section>'


def _parse_dependency_input(raw: str) -> tuple[dict[str, dict[str, Any]], int]:
    raw = raw.strip()
    if not raw:
        return {}, 0
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value, 0
    except json.JSONDecodeError:
        pass
    dependencies: dict[str, dict[str, Any]] = {}
    ignored = 0
    for original in raw.splitlines():
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-e", "--", "git+", "http://", "https://")):
            ignored += 1
            continue
        name_match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not name_match:
            ignored += 1
            continue
        name = name_match.group(1)
        requires_python = ""
        marker = re.search(r"python_version\s*([<>=!~]+)\s*['\"]([^'\"]+)['\"]", line)
        if marker:
            requires_python = f"{marker.group(1)}{marker.group(2)}"
        dependencies[name] = {"requires_python": requires_python, "depends_on": []}
    return dependencies, ignored


def _upgrade(_service: ProductUiService, payload: dict[str, Any]) -> str:
    raw = str(payload.get("dependency_input", ""))
    dependencies = payload.get("dependencies")
    ignored = 0
    if dependencies is None and raw:
        dependencies, ignored = _parse_dependency_input(raw)
    result = None
    target = str(payload.get("target_python", "3.13"))
    if dependencies:
        result = MigrationPlanner().plan(
            target_python=target, dependencies=dependencies
        )
    summary = ""
    if dependencies is not None:
        summary = f'<div class="callout"><strong>{len(dependencies)} dependencies detected</strong><p>{ignored} line needs review</p></div>'
    if result and result.blockers:
        blockers = "".join(
            f"<li><strong>{_esc(b.package)}</strong><span>{_esc(' → '.join(b.path))}</span><small>{_esc(b.constraint)}</small></li>"
            for b in result.blockers
        )
        output = f'<div class="callout warning"><h2>Upgrade blocked</h2><ul class=cards>{blockers}</ul></div>'
    elif result:
        output = '<div class="callout success"><h2>Plan ready</h2><p>No declared Python-version blocker was found. Run the validation checklist next.</p></div>'
    else:
        output = '<div class="empty"><h2>Import dependency data</h2><p>Paste requirements text or dependency JSON to map blockers.</p></div>'
    return f'<section class="panel"><ol class=steps aria-label="Upgrade progress"><li class=active>Import</li><li>Analyze</li><li>Plan</li><li>Validate</li></ol><form method="post" action="/workspace/upgrade" class="stack"><label>Target Python<select name=target_python><option{" selected" if target == "3.13" else ""}>3.13</option><option{" selected" if target == "3.12" else ""}>3.12</option></select></label><label>Dependency data<textarea name=dependencies placeholder="requests>=2.31 or project dependency JSON">{_esc(raw)}</textarea></label><p class="hint">Requirements-style lines and JSON are accepted. Editable and URL dependencies are flagged for review.</p><button class=primary>Analyze compatibility</button></form>{summary}{output}</section>'


def _reviews(service: ProductUiService, payload: dict[str, Any]) -> str:
    actor_packages = set(payload.get("actor_packages", []))
    reviews = service.reviews()
    cards = []
    for review in reviews:
        moderation = (
            ""
            if review["package"] in actor_packages
            else "<button type=button>Hide review</button>"
        )
        cards.append(
            f'<article class="review"><h2>{_esc(review["package"])}</h2><p>{_esc(review["body"])}</p><span>{_esc(review["state"])}</span>{moderation}</article>'
        )
    listing = (
        "".join(cards)
        or '<div class="empty"><h2>No verified reviews</h2><p>Be the first to share evidence-backed package experience.</p></div>'
    )
    return f'<section class="panel"><h2>Write a verified review</h2><form class=stack><label>Package<input name=package required></label><label>Experience<textarea name=body required></textarea></label><label>Lock evidence hash<input name=lock_hash required></label><p class=privacy>Only the evidence hash is published; local paths and dependency contents remain private.</p><button class=primary>Preview review</button></form></section><section class=panel><h2>Review center</h2>{listing}</section>'


def _policy(_service: ProductUiService, payload: dict[str, Any]) -> str:
    if payload.get("sbom"):
        rules = [
            PolicyRule(f"deny-license-{i}", "license", value)
            for i, value in enumerate(payload.get("denied_licenses", []))
        ]
        now = float(payload.get("now", time.time()))
        result = PolicyGate(rules).evaluate(
            payload["sbom"], waivers=payload.get("waivers", []), now=now
        )
        expired = any(
            float(w.get("expires_at", 0)) < now for w in payload.get("waivers", [])
        )
        violations = (
            "".join(f"<li>{_esc(v)}</li>" for v in result.violations)
            or "<li>No active violations</li>"
        )
        expiry = (
            '<div class="callout danger"><strong>Expired waiver</strong><p>Expired exceptions do not change the policy outcome.</p></div>'
            if expired
            else ""
        )
        outcome = f'<div class="outcome {result.outcome.lower()}"><h2>{_esc(result.outcome)}</h2><ul>{violations}</ul></div>{expiry}'
    else:
        outcome = '<div class="empty"><h2>No evaluation yet</h2><p>Upload an SBOM or use dry-run to test a draft policy.</p></div>'
    return f'<section class="panel"><div class="section-heading"><h2>Organization policy</h2><button class=primary>New policy rule</button></div><div class=two-column><div><h3>Visual rule editor</h3><label>Denied license<input placeholder="GPL-3.0"></label><button>Run dry-run</button></div><div><h3>Evaluation</h3>{outcome}</div></div></section><section class=panel><h2>Waiver approval queue</h2><p>Requests show owner, justification, expiration, affected components, and audit history.</p></section>'
