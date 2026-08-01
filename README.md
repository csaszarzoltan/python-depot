# PythonDepot

Python dependency intelligence and governance platform for package discovery, vulnerability monitoring, risk triage, upgrade planning, policy evaluation, and safe migration to `uv`.

[![Version](https://img.shields.io/badge/version-0.10.0-blue)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](./tests)
[![Security](https://img.shields.io/badge/security-dashboard-blue)](./docs/dependency-health.md)
[![Ruff](https://img.shields.io/badge/ruff-passing-brightgreen)](./pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Railway](https://img.shields.io/badge/deploy%20on-Railway-purple)](./railway.toml)

---

## What is new in v0.10

- Filterable, actionable risk inbox with state-preserving updates.
- Atomic bulk triage, persistent owners and due dates, and detailed audit timelines.
- Persistent project workspaces with dependency snapshots and added/removed/changed package deltas.
- One-click reuse of saved project context in upgrade planning, package comparison, and risk filtering.
- Auditable risk transition history and privacy-conscious telemetry hooks.
- Upgrade planner accepts normal requirements text as well as JSON.
- Accessible comparison validation that preserves user input.
- Truthful evidence state instead of claiming unexplored workspaces are current.
- Corrected package configuration and declared form-processing dependency.

See [the v0.7 product engineering report](./docs/v0.7-product-engineering-report.md) for product analysis, requirements, implementation details, tests, and deferred opportunities.

## Product workspaces

| Workspace | Path | Daily-use improvement |
|---|---|---|
| Projects | `/workspace/projects` | Reusable dependency context and immutable snapshots |
| Package decisions | `/workspace/decisions` | Guided shortlist with accessible validation |
| Package trust | `/workspace/trust` | Clear provenance caveats and truthful evidence state |
| Risk inbox | `/workspace/risk-inbox` | Search, state filters, inline state actions, preserved context |
| Python upgrade | `/workspace/upgrade` | Requirements text or JSON input with review feedback |
| Trusted reviews | `/workspace/reviews` | Evidence-backed review workflow |
| SBOM policy | `/workspace/policy` | Policy outcome and waiver visibility |

## Features

| Feature | Description | Key Endpoints |
|---------|-------------|---------------|
| 📦 **Catalog** | Package discovery, CRUD, search, trends | `GET/POST/PUT/DELETE /api/v1/packages/` |
| 🔍 **Search** | Full-text search with pagination | `GET /api/v1/packages/search?q=...&page=...` |
| 📈 **Trends** | Time-series download/star data | `GET /api/v1/packages/{name}/trends?period=7d\|30d\|90d` |
| ⭐ **Ratings** | 1-5 star ratings with distribution | `GET/POST /api/v1/ratings/{name}`, `/summary` |
| 💬 **Reviews** | User reviews with moderation queue | `GET/POST /api/v1/reviews/{name}` |
|| 🔒 **Vulnerabilities** | safety CLI + OSV.dev scanning | `GET/POST /api/v1/vulnerabilities/{name}` |
|| 🛡️ **Security Dashboard** | Health overview, trends, package scoring | `GET /api/v1/dependency-health/*` |
|| ⚠️ **Alerts** | New-vuln detection + webhook delivery | `GET /api/v1/dependency-health/alerts` |
| 📊 **CVSS Scoring** | CVSS v3.1 severity calculation | Built-in `calculate_severity()` |
| 📈 **Analytics** | Trending/popular packages, event tracking | `GET /api/v1/analytics/trending\|popular\|stats/{name}` |
| 📋 **Reports** | Monthly Best-of reports (JSON + HTML) | `GET/POST /api/v1/reports/` |
| 🔄 **uv Migration** | Automated pip/poetry/pipenv → uv migration | `python-depot-migrate --scan ./project` |
| ❤️ **Health** | Detailed health check with DB status | `GET /health` |
| 🛡️ **SSRF Protection** | URL validation on all external calls | Built-in `validate_url()` |

---

## Installation

### Prerequisites

- **Python 3.12+**
- **SQLite** (default, no setup required) or PostgreSQL
- **Safety CLI** (optional, for legacy vulnerability scanning): `pip install safety`
- **httpx** (bundled, for OSV.dev API scanning — no install needed)

### Setup

```bash
# Clone the repository
git clone https://github.com/csaszarzoltan/python-depot.git
cd python-depot

# Install with dev dependencies
pip install -e ".[dev]"

# Run the server
uvicorn python_depot.api:app --reload
```

The API will be available at `http://localhost:8000`.

---

## Quick Start

Once the server is running, try these commands:

```bash
# 1. Check system health
curl http://localhost:8000/health

# 2. List all packages
curl http://localhost:8000/api/v1/packages/

# 3. Search for packages
curl "http://localhost:8000/api/v1/packages/search?q=requests&page=1&page_size=10"

# 4. Get package trends
curl "http://localhost:8000/api/v1/packages/requests/trends?period=7d"

# 5. Submit a rating
curl -X POST http://localhost:8000/api/v1/ratings/requests \
  -H "Content-Type: application/json" \
  -d '{"score": 5}'

# 6. Submit a review
curl -X POST http://localhost:8000/api/v1/reviews/requests \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Excellent HTTP library!", "reviewer": "demo-user"}'

# 7. Check security dashboard
curl http://localhost:8000/api/v1/dependency-health/overview

# 8. Get package health score
curl http://localhost:8000/api/v1/dependency-health/requests/score
```

### Interactive Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Reference

### Catalog & Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API root — version info |
| GET | `/health` | Detailed health check (DB, uptime, version) |
| GET | `/api/v1/packages/` | List all packages |
| POST | `/api/v1/packages/` | Register a new package |
| GET | `/api/v1/packages/{name}` | Get package health report |
| PUT | `/api/v1/packages/{name}` | Update package metadata |
| DELETE | `/api/v1/packages/{name}` | Remove a package |
| GET | `/api/v1/packages/search` | Search packages (`?q=`, `?page=`, `?page_size=`) |
| GET | `/api/v1/packages/{name}/trends` | Download/star trends (`?period=7d\|30d\|90d`) |

### Ratings & Reviews

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ratings/{name}` | Get all ratings for a package |
| POST | `/api/v1/ratings/{name}` | Submit a rating |
| GET | `/api/v1/ratings/{name}/summary` | Rating distribution |
| GET | `/api/v1/reviews/{name}` | List reviews for a package |
| POST | `/api/v1/reviews/{name}` | Submit a review (body: rating, comment, reviewer) |
| GET | `/api/v1/reviews/{name}/{id}` | Get a specific review |

### Vulnerability Scanning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/vulnerabilities/{name}` | List vulnerability scans |
| POST | `/api/v1/vulnerabilities/{name}/scan` | Trigger a new scan |
| GET | `/api/v1/vulnerabilities/{name}/latest` | Get the most recent scan result |

### Security Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dependency-health/overview` | Aggregate vulnerability stats across all packages |
| GET | `/api/v1/dependency-health/trends` | Vulnerability trend data over time |
| GET | `/api/v1/dependency-health/packages` | Packages sorted by health score |
| GET | `/api/v1/dependency-health/alerts` | Recent vulnerability alerts |
| GET | `/api/v1/dependency-health/{name}/score` | Composite security score for a package |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/trending` | Trending packages (7d view growth) |
| GET | `/api/v1/analytics/popular` | Most popular packages |
| POST | `/api/v1/analytics/events` | Track an analytics event |
| GET | `/api/v1/analytics/stats/{name}` | Package view/install stats |

### Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reports/` | List monthly reports |
| POST | `/api/v1/reports/generate` | Generate a report (`?year=`, `?month=`) |
| GET | `/api/v1/reports/{year}/{month}` | Get report JSON |
| GET | `/api/v1/reports/{year}/{month}/html` | Get report HTML |

---

## Deployment

### Railway (one-click)

The project includes `railway.toml` and `Dockerfile` for Railway.

```bash
# Install Railway CLI
npm i -g @railway/cli

# Deploy
railway login
railway init
railway up
```

**Required environment variables** (set in Railway dashboard):
| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | App port | `8000` |
| `DATABASE_URL` | Database connection string | SQLite (local) |
| `PYTHONUNBUFFERED` | Log streaming | `1` |

### Docker

```bash
docker build -t python-depot .
docker run -p 8000:8000 python-depot
```

### Procfile (Heroku / Render)

```bash
web: uvicorn python_depot.api:app --host 0.0.0.0 --port $PORT
```

---

## Development

### Setup

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests (340 behavioral + interface tests)
pytest -v

# Specific module
pytest tests/test_packages.py -v

# With asyncio mode
pytest tests/ --asyncio-mode=auto
```

### Linting

```bash
ruff check .
ruff check --fix .   # auto-fix
```

### Project Structure

```
python-depot/
├── python_depot/              # Core package with extracted modules
│   ├── api.py                 # FastAPI app factory (canonical)
│   ├── database.py            # SQLAlchemy engine + session
│   ├── dependency_health/     # Vulnerability scanner module
│   │   ├── __init__.py
│   │   ├── alerts.py         # AlertEngine with webhook delivery
│   │   ├── models.py         # VulnerabilityScan + VulnerabilityAlert
│   │   ├── osv_client.py     # OSV.dev async API client
│   │   ├── scanner.py        # DependencyScanner + HealthScanner
│   │   └── scoring.py        # CVSS v3.1 calculator + aggregate scoring
│   ├── pydepot/               # PyPI analytics + catalog service
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── catalog.py
│   │   ├── models.py
│   │   └── reports.py
│   ├── ratings/               # Ratings & reviews service
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── service.py
│   ├── routers/               # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── dependency_health.py  # Security dashboard endpoints
│   │   ├── packages.py
│   │   ├── ratings.py
│   │   ├── reports.py
│   │   ├── reviews.py
│   │   └── vulnerabilities.py
│   ├── __init__.py
│   ├── api.py                 # FastAPI app factory (canonical)
│   └── database.py            # SQLAlchemy engine + session
├── src/                       # Legacy source (re-exports from python_depot)
│   ├── app.py                 # → re-exports python_depot.api
│   ├── routers/               # API route handlers
│   │   ├── packages.py
│   │   ├── reviews.py
│   │   ├── ratings.py
│   │   ├── vulnerabilities.py
│   │   ├── analytics.py
│   │   └── reports.py
│   ├── services/              # Service layer classes
│   └── templates/             # Report HTML templates
├── python_depot_migrate/  # uv Migration Assistant CLI
│   ├── __init__.py
│   ├── __main__.py            # python -m python_depot_migrate
│   ├── cli.py                 # CLI entry point + batch mode
│   ├── scanner.py             # Dependency analysis engine
│   ├── compatibility.py       # uv compatibility checker
│   ├── lock_converter.py      # Lock file → uv.lock converter
│   ├── ci_cd.py               # CI/CD config migrator
│   └── report.py              # Markdown + JSON report generator
├── tests/                     # Test suite (340+ tests)
├── docs/                      # Per-feature documentation
├── examples/                  # Runnable Python example scripts
├── Dockerfile                 # Railway/Docker deployment
├── railway.toml               # Railway configuration
├── Procfile                   # Heroku-style process file
└── pyproject.toml             # Project configuration
```

---

## Architecture

PythonDepot uses a modular architecture with three extracted domain modules:

- **dependency_health** — `DependencyScanner` class with async OSV.dev API for vulnerability scanning, `AlertEngine` for new-vuln detection and webhook delivery, `calculate_severity()` for CVSS v3.1 scoring, and `VulnerabilityScan`/`VulnerabilityAlert` models. Legacy `HealthScanner` wrapper for `safety` CLI remains for backward compatibility.
- **pydepot** — `AnalyticsService` (PyPI stats, event tracking), `CatalogService` (PyPI API client), `ReportService` (Jinja2-based monthly reports)
- **ratings** — `RatingService` class with CRUD for ratings and reviews, moderation queue
- **python_depot_migrate** — uv Migration Assistant CLI. Automated pip/poetry/pipenv → uv migration with dependency analysis, compatibility checking, lock file conversion, CI/CD config updates, and markdown/JSON migration reports. Standalone `python-depot-migrate` command. See [docs/uv-migration.md](docs/uv-migration.md) for full guide.

The app factory in `python_depot/api.py` registers all routers and applies four shared patterns:
1. **Health check endpoint** — detailed `/health` with DB status, version, uptime
2. **Security dashboard** — `/api/v1/dependency-health/*` with 5 endpoints for vulnerability monitoring
3. **SSRF protection** — URL validation for all outbound HTTP calls
4. **Railway deploy config** — Dockerfile + `railway.toml` for one-click deploy

---

## License

MIT

---

*PythonDepot — Curated Python package discovery platform*

## Product decision and governance capabilities

Version 0.4 adds six independently usable application services under `python_depot.product`:

- **Decision workspaces** freeze comparable package evidence and produce an auditable decision digest.
- **Release provenance** distinguishes verified attestations, missing evidence, invalid artifacts, and trusted-publisher identity changes.
- **Portfolio watchlists** persist dependency snapshots and create alerts only for changed package risk.
- **Migration planning** identifies direct and transitive packages that block a target Python version.
- **Trusted reviews** require usage evidence and prevent package owners or review authors from moderating their own reviews.
- **SBOM policy gates** evaluate denied metadata, enforce waiver expiration, and isolate private catalog entries by organization.

The main FastAPI application exposes these contracts below `/api/v1/product`. Product persistence defaults to `/tmp/python_depot_product.db` and can be changed with `PYTHONDEPOT_PRODUCT_DB`.

### Product API examples

```bash
curl -X POST http://localhost:8000/api/v1/product/decision-workspaces \
  -H "Content-Type: application/json" \
  -d '{"purpose":"web framework","candidates":["fastapi","flask"]}'

curl -X POST http://localhost:8000/api/v1/product/provenance/evaluate \
  -H "Content-Type: application/json" \
  -d '{"attestation_valid":true,"publisher":"github:org/project","expected_publisher":"github:org/project","artifact_digest_matches":true}'
```

### Isolated capability tests

The repository-wide suite still requires the dependencies declared in `pyproject.toml`. The standard-library product services can be tested in isolation with:

```bash
cp tests/test_product_capabilities.py /tmp/test_product_capabilities.py
cd /tmp
PYTHONPATH=/path/to/python-depot python -m pytest -q test_product_capabilities.py
```

## Product workspaces in 0.5

PythonDepot now provides user-facing workspaces in addition to the versioned APIs:

- `/workspace/decisions` for guided package comparison and decision records.
- `/workspace/trust` for origin, attestation, digest, and publisher-change explanations.
- `/workspace/risk-inbox` for portfolio change triage and acknowledgement.
- `/workspace/upgrade` for Python-version compatibility planning and blocker paths.
- `/workspace/reviews` for evidence-backed reviews and conflict-safe moderation.
- `/workspace/policy` for SBOM policy evaluation, dry runs, waiver review, and private catalog administration.

The workspaces are responsive and server-rendered. Every page includes keyboard navigation, visible recovery guidance, empty and partial states, evidence freshness, and an automation path through the existing JSON APIs. Runtime UI state uses `PYTHONDEPOT_PRODUCT_DB`, defaulting to `/tmp/python_depot_product.db`.

### Testing product workspaces

The isolated UI suite does not require SQLAlchemy:

```bash
cp tests/test_product_ui.py /tmp/test_product_ui.py
cd /tmp
PYTHONPATH=/path/to/python-depot python -m pytest -q test_product_ui.py
```

The complete repository suite still requires the dependencies declared in `pyproject.toml`.
