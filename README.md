# PythonDepot

Curated Python package discovery platform — search, rate, review, and monitor Python packages through a single FastAPI service.

[![Tests](https://img.shields.io/badge/tests-176%20passed-brightgreen)](./tests)
[![Security](https://img.shields.io/badge/security-dashboard-blue)](./docs/dependency-health.md)
[![Ruff](https://img.shields.io/badge/ruff-passing-brightgreen)](./pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Railway](https://img.shields.io/badge/deploy%20on-Railway-purple)](./railway.toml)

---

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
|| 📊 **CVSS Scoring** | CVSS v3.1 severity calculation | Built-in `calculate_severity()` |
|| 📈 **Analytics** | Trending/popular packages, event tracking | `GET /api/v1/analytics/trending\|popular\|stats/{name}` |
| 📋 **Reports** | Monthly Best-of reports (JSON + HTML) | `GET/POST /api/v1/reports/` |
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
# All tests (176 behavioral + interface tests)
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
├── tests/                     # Test suite (176+ tests)
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
