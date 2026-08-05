# PythonDepot

Python dependency intelligence and governance platform for package discovery, vulnerability monitoring, risk triage, upgrade planning, policy evaluation, and safe migration to `uv`.

[![Version](https://img.shields.io/badge/version-0.11.0-blue)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](./tests)
[![Security](https://img.shields.io/badge/security-dashboard-blue)](./docs/dependency-health.md)
[![Ruff](https://img.shields.io/badge/ruff-passing-brightgreen)](./pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Railway](https://img.shields.io/badge/deploy%20on-Railway-purple)](./railway.toml)

---

## What is new in v0.11

- **Offline-capable PyPI caching proxy (PEP 503 simple index)** — a standalone FastAPI proxy that fronts PyPI with a persistent SQLite-backed cache. Point `pip` at it (`pip config set global.index-url http://127.0.0.1:<port>/simple/`) and installs are served from cache; `PYTHONDEPOT_OFFLINE_MODE=1` turns it into a cache-only fallback for air-gapped networks. Includes cache warm-up (`POST /api/v1/cache/warmup` + CLI) and analytics (`GET /api/v1/cache/analytics`: hit rate, bytes served vs proxied). See [docs/offline-cache.md](docs/offline-cache.md).
- **Supply-chain attack detection** — typosquatting (edit-distance + prefix/suffix similarity against a popular-package corpus) and known-malicious feed integration, combined with download-count and release-freshness heuristics into a 0-100 risk score with human-readable reasons. See [docs/supply-chain.md](docs/supply-chain.md).

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
| 🔒 **Vulnerabilities** | safety CLI + OSV.dev scanning | `GET/POST /api/v1/vulnerabilities/{name}` |
| 🛡️ **Security Dashboard** | Health overview, trends, package scoring | `GET /api/v1/dependency-health/*` |
| ⚠️ **Alerts** | New-vuln detection + webhook delivery | `GET /api/v1/dependency-health/alerts` |
| 🧬 **Supply Chain** | Typosquatting + malicious-package detection | `GET /api/v1/supply-chain/check\|scan` |
| 📦 **Offline Cache Proxy** | PEP 503 PyPI caching proxy w/ offline fallback | `GET /simple/{package}/`, `/api/v1/cache/analytics\|warmup` |
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

# 9. Check a package for typosquatting / malicious-package risk
curl "http://localhost:8000/api/v1/supply-chain/check?package=requets"
```

### Install packages through the caching proxy

Run the standalone PEP 503 caching proxy (it does not need the main API):

```bash
# Start the proxy on port 8765
uvicorn python_depot.routers.pep503:create_proxy_app --factory --port 8765

# Point pip at it — installs are served from cache; the first run proxies PyPI
pip config set global.index-url http://127.0.0.1:8765/simple/
pip config set global.trusted-host 127.0.0.1
pip install requests
```

Set `PYTHONDEPOT_OFFLINE_MODE=1` when starting the proxy for cache-only (air-gapped) operation. See [docs/offline-cache.md](docs/offline-cache.md) for warm-up, analytics, and offline usage.

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

### Supply-Chain Scanning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/supply-chain/check` | Typosquatting verdict for a single package (`?package=`) |
| GET | `/api/v1/supply-chain/scan` | Verdicts for the dependency set (20 popular packages) |

Both endpoints return a 0-100 risk score (`score`) plus a `reasons` array of human-readable detection signals (known-malicious membership, name similarity to a popular package, low download count, recently published). See [docs/supply-chain.md](docs/supply-chain.md) for the full reference and score semantics.

### Offline Cache Proxy

| Method | Path | Description |
|--------|------|-------------|
| GET | `/simple/{package}/` | PEP 503 simple index (cached version list; proxies upstream on a miss; `503` when uncached in offline mode) |
| GET | `/simple/{package}/{filename}` | Cached wheel/sdist artifact bytes (proxies + caches missing artifacts; `503` when unavailable in offline mode) |
| GET | `/api/v1/cache/analytics` | Cache analytics: `hit_rate`, `bytes_served`, `bytes_proxied`, `per_package` stats |
| POST | `/api/v1/cache/warmup` | Prefetch packages: body `{"top_n": 10}` or `{"packages": ["six"]}`; returns `{requested, cached, failed}` |

These routes live on the standalone proxy app (`uvicorn python_depot.routers.pep503:create_proxy_app --factory`) and are not mounted on the main API. The proxy is SSRF-guarded (host allowlist + IP-range check) and is **not an open proxy** — it can only fetch from PyPI. See [docs/offline-cache.md](docs/offline-cache.md) for quickstart, offline/air-gapped usage, and warm-up CLI usage.

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
| `PYTHONDEPOT_OFFLINE_MODE` | Cache-only fallback for the PyPI proxy (`1`/`true`/`yes`) | unset (online) |

The caching proxy is a separate process (`uvicorn python_depot.routers.pep503:create_proxy_app --factory`); see [docs/offline-cache.md](docs/offline-cache.md) for its full configuration (`PYTHONDEPOT_CACHE_DIR`, `PYTHONDEPOT_CACHE_TTL`, `PYTHONDEPOT_CACHE_MAX_BYTES`).

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
│   ├── supply_chain.py         # Typosquatting + malicious-package scanner
│   ├── pep503_cache.py         # PEP 503 caching proxy service (PyPICacheService)
│   ├── artifact_store.py       # On-disk wheel/sdist artifact storage
│   ├── warmup.py               # Cache warm-up service + CLI (main)
│   ├── models/                 # SQLAlchemy models
│   │   ├── pep503_cache.py     # CachedPackage + CachedArtifact
│   ├── routers/               # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── dependency_health.py  # Security dashboard endpoints
│   │   ├── packages.py
│   │   ├── pep503.py           # Offline cache proxy app + routes (create_proxy_app)
│   │   ├── ratings.py
│   │   ├── reports.py
│   │   ├── reviews.py
│   │   ├── supply_chain.py   # Supply-chain typosquatting endpoints
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

The offline PyPI caching proxy is a **separate FastAPI app** (`python_depot.routers.pep503.create_proxy_app`) that mounts `pep503.router` + `pep503.artifact_router` and shares the same SQLite database. It is deliberately not part of `create_app()` (the app route set is contract-pinned). See [docs/offline-cache.md](docs/offline-cache.md).

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
