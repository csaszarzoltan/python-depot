# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
