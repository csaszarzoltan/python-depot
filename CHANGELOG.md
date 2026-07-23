# Changelog

All notable changes to PythonDepot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-23

### Added

- **FastAPI app factory** (`python_depot/api.py`) with all registered routers:
  - Packages (CRUD, search, trends)
  - Reviews (list, submit, get-by-id)
  - Ratings (list, submit, summary)
  - Vulnerabilities (list, trigger-scan, latest)
  - Analytics (trending, popular, events, stats)
  - Reports (list, generate, get-json, get-html)
- **Shared patterns applied**:
  - Health check endpoint (`/health`) with DB status, uptime, version, sub-checks
  - SSRF protection (`validate_url()` with ALLOWED_SCHEMES, BLOCKED_HOSTS, BLOCKED_IP_RANGES)
  - Railway deploy config (`Dockerfile` + updated `railway.toml`)
- Pre-dev contract test suite (17 behavioral tests covering all endpoints)
- `Dockerfile` for Railway deployment (python:3.12-slim, uv, non-root user)
- `python_depot/__init__.py` package root
- Pydantic validation on review submission (rating 1-5, comment, reviewer)
- 422 error for invalid package names (PEP 508 regex)
- Search with pagination (`?q=`, `?page=`, `?page_size=`)
- Trends with period parameter (`?period=7d|30d|90d`)

### Changed

- `src/app.py` re-exports from `python_depot.api` for backward compatibility
- `src/routers/packages.py` — added `GET /search`, `GET /{name}/trends`, validation regex, 404 for non-existent packages
- `src/routers/reviews.py` — Pydantic body validation, 201 response with review_id + timestamp
- `pyproject.toml` — package find includes both `src/` and `python_depot/`
- `railway.toml` — DOCKERFILE builder, environments prod/staging, startCommand targets `python_depot.api:app`
- Tests updated for new contracts (404 vs 200, `ok` vs `healthy`)

## [0.1.0] - 2026-07-22

### Added

- **Extracted domain modules** (3 modules, 10 sub-packages):
  - `python_depot/dependency_health/` — `HealthScanner` (safety CLI wrapper), `VulnerabilityScan` model
  - `python_depot/pydepot/` — `AnalyticsService` (PyPI stats, event tracking), `CatalogService` (PyPI API), `ReportService` (Jinja2 reports), `Package`, `AnalyticsEvent`, `MonthlyReport` models
  - `python_depot/ratings/` — `RatingService` (CRUD, moderation queue), `Rating`, `Review` models
- **Service layer** with 5 domain services:
  - `catalog_service.py` — PyPI JSON API client, SQLite storage, search
  - `rating_service.py` — Rating/review CRUD, moderation queue
  - `health_service.py` — Safety CLI integration, compatibility checks
  - `analytics_service.py` — Event tracking, download stats
  - `report_service.py` — Jinja2 template engine for monthly Best-of reports
- `python_depot/database.py` — Shared SQLAlchemy engine, session, Base, and `get_db`/`init_db`
- `MonthlyReport` model with year/month unique constraint
- Reports router with 4 endpoints (`/api/v1/reports/`)
- Self-contained HTML report template (`src/templates/report.html`)
- `aiohttp` for async PyPI API calls
- `jinja2` for report template rendering
- SQLite database configuration (default)
- FastAPI application with app factory pattern
- SQLAlchemy models: Package, Rating, Review, VulnerabilityScan, AnalyticsEvent
- API routers: packages, ratings, reviews, vulnerabilities, analytics
- Health check endpoint at `/health`
- GitHub Actions CI (Python 3.10, 3.11, 3.12)
- Ruff linting configuration
- Test suite with pytest + httpx (14 tests)

### Fixed

- Missing moderation columns on Review model
- Stub routers replaced with real service integrations
- N+1 query in ReportService.generate_report
- Bare Exception masking specific error types
- Wrong compatibility data in health service

### Quality Metrics

- **Test Coverage**: 50/50 tests passing (34 interface + 17 behavioral)
- **Code Quality**: Ruff check clean, 0 warnings
- **Documentation**: README, 5 feature guides, 3 runnable examples
- **Deployment**: Multi-platform (Railway Docker, Heroku Procfile)
- **Security**: SSRF protection, vulnerability scanning via safety CLI
