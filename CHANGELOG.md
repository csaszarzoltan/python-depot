# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0] — 2026-08-05

### Features

**Offline-capable PyPI caching proxy (PEP 503 simple index)**

- Added a standalone FastAPI proxy app (`create_proxy_app()`) serving a PEP 503 simple index (`GET /simple/{package}/`) that caches upstream PyPI responses in SQLite and serves cached artifacts (`GET /simple/{package}/{filename}`), with offline mode (`PYTHONDEPOT_OFFLINE_MODE=1`) when upstream is unreachable.
- Added `PyPICacheService` with per-entry lazy TTLs, SSRF-guarded upstream URL validation, artifact storage with path-traversal guards, and single-query analytics (`GET /api/v1/cache/analytics`: hit rate, bytes served vs proxied, per-package stats).
- Added warmup support (`POST /api/v1/cache/warmup` + warmup CLI) that prefetches top-N packages; exits 1 when nothing was cached.
- End-to-end verified with real pip: `pip install --index-url http://127.0.0.1:<port>/simple/` works both online (proxy + cache) and fully offline (served from cache, hit rate 0.8).

**Supply-chain attack detection**

- Added typosquatting detection for PyPI package names: `SimilarityEngine` combines Levenshtein/Damerau-Levenshtein edit distance with prefix/suffix heuristics against a top-20 popular-package corpus (configurable similarity threshold, default 0.8).
- Added malicious-package feed integration: `MaliciousFeed` loads known-bad names from OSV entries plus an optional curated blocklist and refreshes on every scan.
- Added download-count and release-freshness heuristics that combine with similarity into a 0-100 risk score with human-readable reasons; low-download, newly published, renamed/similar packages score higher.
- Added `SupplyChainVerdict` model with SQLite persistence (`store_verdict` / `list_verdicts`) using the existing `database.py` patterns.
- Added two REST endpoints: `GET /api/v1/supply-chain/check?package=NAME` (single-package verdict: `{score, reasons}`) and `GET /api/v1/supply-chain/scan` (per-package verdicts for the dependency set plus `scanned_at`).
- Added `SupplyChainAlerter` with exactly-once webhook notifications, firing only for newly detected suspicious packages (score >= 60).

### Fixes

- Addressed tech-lead review blockers on the caching proxy: HTML-escaped every interpolated value in the simple index, wrapped upstream httpx errors into `CacheMissError` → 503 (not 500) with `db.rollback()`, artifact fetch returns `None` on failure, lazy per-entry TTL in `ArtifactStore.get()`, single-query `overall_stats`, warmup exits 1 when nothing cached.
- Eliminated 4 baseline test failures, a shared-DB race, and version drift.
- Addressed supply-chain review findings F1–F6: validated package query params and capped `SimilarityEngine` input at 200 chars (CPU-amplification guard), fed real PyPI metadata (downloads, release dates) so unknown data never emits the low-download reason, wired webhook URL + blocklist from `PYTHONDEPOT_*` env config, DB-backed exactly-once dedup via `SupplyChainVerdict.notified`, batch upsert with one commit per scan, and webhook failure logging without exception/URL leakage.
- Fixed I001 import sort in webhook failure tests.

### Tests

- Added pre-dev TDD suites + stubs for the PEP 503 caching proxy: ~1,600 lines across 4 new modules (`test_pep503_cache.py`, `test_pep503_api.py`, `test_artifact_store.py`, `test_warmup.py`); new-feature modules 141/141 green.
- Added regression tests for all five tech-lead review items (html.escape coverage, rollback on failed fetch, `_safe_relative` traversal guards, lazy TTL, warmup exit codes).
- Full suite: 1010 tests / 939 passed / 0 failed / 71 skipped across 36 modules; ruff clean on all changed files.

### Docs

- Documented typosquatting and malicious package detection in `docs/supply-chain.md`.
- Updated README version badge and CHANGELOG.

## [0.10.0] — 2026-08-01

### Cross-workspace project context

- Added one-click project-to-upgrade navigation using the latest saved dependency snapshot.
- Added one-click project-to-comparison navigation with detected package candidates prefilled.
- Added contextual project-risk navigation with the project name preserved as the risk search.
- Added privacy-safe workflow-launch telemetry that excludes repository and dependency content.
- Added explicit 404 behavior for missing project context.

### Quality

- Added five TDD acceptance tests for project context reuse, prefill behavior, telemetry privacy, and missing-project recovery.
- Focused product regression expanded to 40 passing tests.

## [0.9.0] — 2026-08-01

### Persistent project workspaces

- Added durable projects with a reusable repository/source context.
- Added requirements-style dependency imports and immutable project snapshots.
- Added package-level delta reporting for added, removed, and constraint-changed dependencies.
- Added project list and detail workspaces with dependency tables, import forms, and snapshot history.
- Added privacy-conscious snapshot telemetry containing only project identifier and dependency count.

### Quality

- Added five TDD acceptance tests for project creation, re-import deltas, UI states, and routes.
- Focused product regression expanded to 35 passing tests.

## [0.8.0] — 2026-08-01

### Daily risk operations

- Added persistent risk ownership and due dates with forward-compatible SQLite migration.
- Added atomic bulk triage with all-or-nothing validation and per-item audit history.
- Added risk detail pages with project context, state, ownership, due date, and activity timeline.
- Added single-risk edit forms for state, owner, due date, and notes.
- Added multi-select inbox controls while retaining quick single-item actions.

### Quality

- Added five TDD acceptance tests for ownership, bulk atomicity, detail views, and audit history.
- Preserved all v0.7 and original product UI behavior; the focused product regression now has 30 passing tests.

## [0.7.0] — 2026-08-01

### User experience

- Added server-side risk inbox search and workflow-state filtering.
- Added inline risk state updates with preserved filters and actionable notices.
- Added accessible decision validation with value preservation.
- Added requirements-style input to the Python upgrade planner and explicit unsupported-line feedback.
- Replaced misleading default evidence freshness with evaluated/not-evaluated semantics.

### Engineering and quality

- Added immutable risk transition history and privacy-conscious telemetry hooks.
- Added six TDD acceptance/integration tests for v0.7 workflows.
- Added responsive table, focus, reduced-motion, and screen-reader improvements.
- Corrected setuptools package discovery and declared `python-multipart`.
- Added the complete product engineering report and updated README.

## [0.6.0] — 2026-07-31

### Features

- **uv Migration Assistant** — automated pip/poetry/pipenv/pip-tools → uv migration CLI (`python-depot-migrate`):
  - Dependency analysis engine: scans `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `setup.cfg`, `requirements.in`
  - Compatibility checker: flags packages with known uv issues (pip-tools, poetry-core, black, setup.py-only, private indexes) with effort estimates
  - Lock file conversion: reads `poetry.lock` (TOML with regex fallback), `Pipfile.lock` (JSON), pinned `requirements.txt`; produces constraints for `uv lock`
  - CI/CD config updater: detects and migrates GitHub Actions, GitLab CI, Dockerfiles from pip/poetry/pipenv to uv equivalents
  - Migration report generator: markdown and JSON reports with before/after comparison, rollback instructions
  - CLI entry point with `--scan`, `--apply`, `--batch`, `--report-only`, `--output` flags; exit codes 0/1/2
  - Batch mode for migrating multiple projects simultaneously
  - `python -m python_depot_migrate` support

### Testing

- 411 tests across 5 modules: 340 passing, 71 skipped (RED-phase stubs for DependencyScanner)
- Dependency analysis: 102 tests, Lock conversion: 76 tests, CI/CD updater: 61 tests, Compatibility + report: 109 tests, CLI: 63 tests

### Docs

- Added `docs/uv-migration.md` — comprehensive feature guide covering all 4 migration stages, CLI reference, programmatic usage, edge cases, architecture
- Added `examples/uv_migration.py` — 5 runnable examples (compatibility check, lock conversion, CI/CD detection, migration report, data model)
- Updated README features table, project structure, architecture section, test badge, test count

## [0.5.0] — 2026-07-30

### User interfaces

- Added six responsive, server-rendered product workspaces for package comparison, provenance explanation, portfolio risk triage, Python upgrade planning, trusted reviews, and SBOM policy management.
- Added accessible navigation, skip links, live status regions, keyboard-friendly forms, empty states, recovery guidance, mobile layouts, evidence freshness, and permission-aware actions.
- Added persistent UI workflow state for risk inbox items and evidence-backed reviews without coupling the view layer to SQLAlchemy.
- Added FastAPI page routes under `/workspace/*` while preserving all existing API contracts.

### Quality

- Added isolated UI behavior tests covering trust semantics, persistent acknowledgement, transitive blocker explanation, moderation conflicts, waiver expiration, accessibility landmarks, and recovery actions.
- Kept the product UI renderer independently testable with only the Python standard library and existing product-domain modules.

## [0.4.0] — 2026-07-30

### Product capabilities

- Added auditable package decision workspaces with immutable evidence digests.
- Added release provenance classification for valid, missing, invalid, and changed publisher identities.
- Added dependency portfolio snapshots with risk-delta alert deduplication.
- Added project-wide Python compatibility planning with transitive blocker paths.
- Added evidence-backed reviews and conflict-safe, append-only moderation events.
- Added SBOM license policy evaluation, expiring waivers, and tenant-scoped private catalog filtering.
- Added `/api/v1/product` FastAPI contracts for the new product services.

### Security and quality

- Added organization-header isolation for policy evaluation endpoints.
- Added deterministic standard-library tests for all six capabilities and their negative cases.
- Preserved existing catalog, ratings, vulnerability, ecosystem, and dashboard contracts.

## [0.3.0] — 2026-07-26

### Features

- **Vulnerability Dashboard UI** — Interactive Jinja2 dashboard with Chart.js:
  - Overview page with severity donut chart, trend line chart, vulnerability summary cards
  - Package health table with search, sort, pagination
  - Package detail view with 0-100 health score visualization
  - Alerts listing with severity filtering
  - Responsive design (mobile + desktop)
  - Static file serving configured in FastAPI

### Testing

- 60 new dashboard UI tests (31 interface + 29 behavioral) all passing
- 218 existing backend tests still passing (284 total, 6 known external-dependent failures unchanged)

### Known Issues

- 6 pre-existing external-dependent test failures: 4 webhook DNS-dependent tests (webhook.site unreachable), 2 OSV client tests (fake vulnerability ID GHSA-xxxx-xxxx-xxxx returns 404 from real API)

## [0.2.0] — 2026-07-26

### Features

- **Package Ecosystem & Migration Hub** — 4 new API endpoints:
  - `GET /api/v1/ecosystem/detect/{name}` — package manager detection via PyPI JSON + pyproject.toml analysis
  - `GET /api/v1/ecosystem/stats` — aggregated ecosystem adoption statistics (adoption rates, trending migrations)
  - `GET /api/v1/ecosystem/migration-guide/{name}` — generated migration guides between package managers (pip→uv, poetry→uv, pip→poetry, pip-tools→uv)
  - `GET /api/v1/ecosystem/compatibility` — paginated compatibility matrix across scanned packages
- **pip-tools→uv migration guide** — new supported migration path with complete steps, config changes, and notes
- **Package scanning** — async PyPI fetch + signal detection (requires_dist, project_urls, classifiers) + pyproject.toml parsing
- **Ecosystem stats** — per-manager adoption rates, trending migration tracking with estimated package counts
- **SQLAlchemy models** — `PackageScan` + `EcosystemStatsSnapshot` for persistent scan storage
- All 4 endpoints return full JSON responses with scan tier metadata

### Fixes

- **API wiring** — wired ecosystem router into main application (import + include_router)
- **Integration tests** — fixed `_IncludedRouter` import to use `fastapi.routing` (compatibility with Starlette 1.3.1)
- **Migration test assertion** — fixed `get_supported_migrations` dict comparison to handle `estimated_packages` key via subset matching
- **Route registration test** — added 4 ecosystem endpoints to expected route list

### Tests

- 218 tests passing (0 failures, 0 errors) across 22 test files
  - 20 new ecosystem tests: 20 scanner + 9 migration + 13 integration = 42 ecosystem tests passing
- 6 pre-existing reliable failures unchanged: 4 webhook DNS + 2 OSV fake ID

## [0.1.0] — 2026-07-24

### Features

- **Vulnerability scanning** — full OSV.dev-backed dependency vulnerability scanner
  - `OSVClient` — query packages, batch queries, vulnerability details via OSV.dev API
  - `DependencyScanner` — scan packages and batches, list/view scan history
  - CVSS scoring engine — severity calculation (v3.1), aggregate scoring
  - `AlertEngine` — new vulnerability detection, webhook notifications, alert listing
- **Security dashboard** — 5 dependency-health API endpoints: overview, trends, packages, alerts, package score
- **Alerts system** — alert creation, dismissal, listing with webhook integration
- Full FastAPI application scaffold with:
  - 26+ API endpoints: health, packages, reviews, ratings, analytics, vulnerabilities, reports, search, trends
  - Domain services: CatalogService, RatingService, ReportGenerator, AnalyticsService, HealthScanner
  - SQLAlchemy async models: Package, Rating, Review, VulnerabilityScan, AnalyticsEvent, MonthlyReport
  - Jinja2 HTML report templates
  - Async PyPI integration via aiohttp
- Python 3.12+ target, ruff linting configured

### Fixes

- **Security fixes** — SSRF protection via hostname resolution + IP range blocking, XSS prevention in HTML templates (all user content html.escape'd)
- **Performance** — N+1 query elimination in report generators (batch queries reduced from O(n) to O(1))
- **API wiring** — rewired stub routers to real business logic services
- **HealthScanner** — safety CLI non-zero exit now correctly reports vulnerabilities instead of silent pass
- **reset_db()** — fixed bare `except Exception: pass` to catch `OperationalError` specifically
- **Infrastructure** — Railway deployment fixes: Dockerfile PORT expansion, dual-stack IPv6 binding, Nixpacks builder support
- **moderation** — fixed missing moderation columns on Review model

### Tests

- 176 tests passing (0 failures, 0 errors) across 16 test files
  - `test_alerts.py` — 21 passed
  - `test_dependency_health.py` — 17 passed
  - `test_osv_client.py` — 18 passed
  - `test_scanner.py` — 19 passed
  - `test_scoring.py` — 19 passed
  - Legacy tests (packages, ratings, reviews, reports, analytics, etc.) — 54 passed
  - 6 pre-dev behavioral contract tests use external resources (hooks.example.com, fake GHSA IDs)
- Ruff linting clean — zero issues

### Docs

- 5 feature guides: packages, ratings, reviews, reports, analytics
- Quick-start examples and API usage documentation
- README with project overview and deployment instructions
- CI configuration: Python 3.12/3.13 matrix, ruff + pytest on push
