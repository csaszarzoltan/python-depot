# Dependency Health & Vulnerability Scanning

PythonDepot provides a comprehensive security scanning suite built on the [OSV.dev](https://osv.dev/) open-source vulnerability database. It includes CVSS v3.1 scoring, alerting with webhook delivery, and a security dashboard for monitoring across all packages.

---

## Architecture

```
                ┌─────────────────────┐
                │   OSV.dev API        │
                │  api.osv.dev/v1/     │
                └──────┬──────────────┘
                       │ HTTP (httpx)
                ┌──────▼──────────────┐
                │   OSVClient          │  ← query_package, query_batch, get_vuln_details
                └──────┬──────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐  ┌──────────┐  ┌─────────┐
   │Dependency│  │ Health   │  │ CVSS    │
   │Scanner   │  │ Scanner  │  │ Scoring │
   │(OSV.async)│  │(safetyCLI)│  │ Engine  │
   └────┬─────┘  └────┬─────┘  └────┬────┘
        │              │             │
        └──────────────┼─────────────┘
                       ▼
                ┌──────────────┐
                │ AlertEngine  │  ← detects new vulns, fires webhooks
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │  Dashboard   │  ← 5 REST endpoints
                │  (overview,  │
                │   trends,    │
                │   packages,  │
                │   alerts,    │
                │   scores)    │
                └──────────────┘
```

## Modules

### OSVClient

`python_depot.dependency_health.osv_client.OSVClient`

Async HTTP client for the [OSV.dev REST API](https://osv.dev/docs/). Queries vulnerabilities by package name/version and retrieves full vulnerability details.

| Method | Description | Returns |
|--------|-------------|---------|
| `query_package(name, version=None)` | Query vulnerabilities for a PyPI package | `dict` with `vulns` list |
| `query_batch(queries)` | Batch query multiple packages | `list[dict]` |
| `get_vuln_details(vuln_id)` | Fetch full details for a vulnerability ID | `dict` |

**Example:**

```python
from python_depot.dependency_health.osv_client import OSVClient

async def example():
    client = OSVClient()

    # Query a specific version
    result = await client.query_package("requests", "2.31.0")
    # → {"vulns": [{"id": "GHSA-xxxx", ...}]}

    # Query all known vulnerabilities (no version)
    result = await client.query_package("requests")

    # Batch query
    results = await client.query_batch([
        {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.31.0"},
        {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "2.3.0"},
    ])

    # Get vulnerability details
    details = await client.get_vuln_details("GHSA-xxxx-xxxx-xxxx")
```

### DependencyScanner

`python_depot.dependency_health.scanner.DependencyScanner`

Async vulnerability scanner backed by OSV.dev. Replaces the legacy `HealthScanner` with non-blocking queries. Maintains backward-compatible response format.

| Method | Description |
|--------|-------------|
| `scan_package(name, version=None)` | Scan a package via OSV.dev, persist result to DB |
| `scan_batch(packages)` | Scan multiple packages sequentially |
| `list_scans(pkg_id, name)` | List all scans for a package |
| `latest_scan(pkg_id, name)` | Get the most recent scan result |

**Scan result format:**

```json
{
  "package": "requests",
  "version": "2.31.0",
  "status": "clean",
  "vulnerability_count": 0,
  "scan_id": 1
}
```

Status values: `clean` (no vulns), `vulnerable` (found), `unknown` (scan error).

### HealthScanner

`python_depot.dependency_health.scanner.HealthScanner`

Legacy synchronous scanner wrapping the `safety` CLI. Used by the `/api/v1/vulnerabilities/` endpoints.

| Method | Description |
|--------|-------------|
| `scan_package(package_name, pkg_id, version=None)` | Run safety CLI, persist result |
| `list_scans(pkg_id, package_name)` | List all scans for a package |
| `latest_scan(pkg_id, package_name)` | Get most recent scan |
| `get_compatibility(package_name, latest_version=None)` | Build compatibility matrix |

### CVSS v3.1 Scoring Engine

`python_depot.dependency_health.scoring`

Implements the CVSS v3.1 base score formula as published by [FIRST.org](https://www.first.org/cvss/v3-1/).

| Function | Description |
|----------|-------------|
| `calculate_severity(cvss_vector)` | Parse a CVSS v3.1 vector → score (0–10) + severity label |
| `aggregate_score(vulns)` | Aggregate multiple vulns into a composite health score |

**`calculate_severity` return:**

```json
{
  "score": 9.8,
  "severity": "CRITICAL",
  "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
}
```

Severity labels: `NONE` (0), `LOW` (0.1–3.9), `MEDIUM` (4.0–6.9), `HIGH` (7.0–8.9), `CRITICAL` (9.0–10.0).

**Valid vector format:**

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

Where:
- `AV` — Attack Vector: `N` (Network), `A` (Adjacent), `L` (Local), `P` (Physical)
- `AC` — Attack Complexity: `L` (Low), `H` (High)
- `PR` — Privileges Required: `N` (None), `L` (Low), `H` (High)
- `UI` — User Interaction: `N` (None), `R` (Required)
- `S` — Scope: `U` (Unchanged), `C` (Changed)
- `C`/`I`/`A` — Confidentiality/Integrity/Availability Impact: `N` (None), `L` (Low), `H` (High)

**`aggregate_score` return:**

```json
{
  "total": 7.5,
  "max_severity": "HIGH",
  "vuln_count": 3,
  "avg_score": 6.2,
  "breakdown": {
    "NONE": 0, "LOW": 1, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0
  }
}
```

### AlertEngine

`python_depot.dependency_health.alerts.AlertEngine`

Detects newly discovered vulnerabilities by comparing scan results against historical data, fires webhook notifications for alerts meeting the configured severity threshold, and provides alert history.

| Method | Description |
|--------|-------------|
| `check_new_vulns(package_name, current_scan)` | Compare current scan vs previous → list of new vulns |
| `fire_webhook(alert, webhook_url=None)` | POST alert payload to webhook URL |
| `list_alerts(package_name=None, severity=None)` | List alert history with optional filters |

**Constructor parameters:**

| Param | Default | Description |
|-------|---------|-------------|
| `db` | required | SQLAlchemy session |
| `webhook_url` | `None` | URL for alert webhook delivery |
| `severity_threshold` | `"MEDIUM"` | Minimum severity that triggers webhooks |

**Webhook payload:**

```json
{
  "event": "vulnerability_alert",
  "severity": "CRITICAL",
  "package": "requests",
  "vuln_id": "GHSA-xxxx-xxxx-xxxx",
  "score": 9.8,
  "timestamp": "2026-07-24T00:00:00Z",
  "details": "..."
}
```

---

## REST API

### Legacy Vulnerability Scanning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/vulnerabilities/{name}` | List vulnerability scans |
| POST | `/api/v1/vulnerabilities/{name}/scan` | Trigger a new scan |
| GET | `/api/v1/vulnerabilities/{name}/latest` | Get most recent scan result |

### Security Dashboard

Five endpoints exposing aggregate security data across all packages:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dependency-health/overview` | Aggregate vulnerability statistics |
| GET | `/api/v1/dependency-health/trends` | Vulnerability trend data over time |
| GET | `/api/v1/dependency-health/packages` | Packages sorted by health score |
| GET | `/api/v1/dependency-health/alerts` | Recent vulnerability alerts |
| GET | `/api/v1/dependency-health/{name}/score` | Composite security score for a package |

#### GET `/api/v1/dependency-health/overview`

Aggregate vulnerability stats across all scanned packages.

**Response:**

```json
{
  "total_packages": 42,
  "total_scans": 156,
  "vuln_counts": {
    "vulnerable": 3,
    "clean": 148,
    "unknown": 5
  },
  "severity_breakdown": {},
  "scan_coverage": 94.9,
  "last_scan": "2026-07-24T12:00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_packages` | int | Unique packages with at least one scan |
| `total_scans` | int | Total scan records across all packages |
| `vuln_counts` | object | Count by scan status (vulnerable/clean/unknown) |
| `scan_coverage` | float | Percentage of scans reporting clean |
| `last_scan` | str | ISO 8601 timestamp of the most recent scan |

#### GET `/api/v1/dependency-health/trends`

Time-series vulnerability data. Each entry shows cumulative scan counts at a point in time.

**Response:**

```json
{
  "trends": [
    {
      "timestamp": "2026-07-01T10:00:00",
      "vulnerable": 1,
      "clean": 10,
      "unknown": 0,
      "total": 11
    }
  ]
}
```

#### GET `/api/v1/dependency-health/packages`

List packages sorted by health score.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `sort_by` | string | `"score"` | Sort field: `score`, `name`, `vuln_count` |
| `limit` | int | `20` | Max results |
| `offset` | int | `0` | Pagination offset |

**Response:**

```json
{
  "packages": [
    {
      "package_id": 1,
      "vuln_count": 0,
      "status": "clean",
      "last_scan": "2026-07-24T12:00:00"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### GET `/api/v1/dependency-health/alerts`

List recent vulnerability alerts.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `severity` | string | — | Filter by severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `limit` | int | `50` | Max results |
| `offset` | int | `0` | Pagination offset |

**Response:**

```json
{
  "alerts": [
    {
      "id": 1,
      "package_name": "requests",
      "vuln_id": "GHSA-xxxx-xxxx-xxxx",
      "severity": "HIGH",
      "score": 7.5,
      "webhook_status": "sent",
      "created_at": "2026-07-24T12:00:00"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

#### GET `/api/v1/dependency-health/{name}/score`

Composite 0–100 security score for a package (100 = no known vulnerabilities).

**Response:**

```json
{
  "package": "requests",
  "score": 85.0,
  "breakdown": {
    "base_score": 85.0,
    "vuln_penalty": 15.0
  },
  "vuln_count": 2,
  "max_severity": "HIGH",
  "score_label": "GOOD"
}
```

| Score Range | Label |
|-------------|-------|
| 90–100 | `EXCELLENT` |
| 70–89 | `GOOD` |
| 50–69 | `FAIR` |
| 30–49 | `POOR` |
| 0–29 | `CRITICAL` |

---

## Shell Usage

```bash
# Legacy vulnerability endpoints
curl http://localhost:8000/api/v1/vulnerabilities/requests
curl -X POST http://localhost:8000/api/v1/vulnerabilities/requests/scan
curl http://localhost:8000/api/v1/vulnerabilities/requests/latest

# Security dashboard
curl http://localhost:8000/api/v1/dependency-health/overview
curl http://localhost:8000/api/v1/dependency-health/trends
curl http://localhost:8000/api/v1/dependency-health/packages
curl http://localhost:8000/api/v1/dependency-health/alerts?severity=HIGH
curl http://localhost:8000/api/v1/dependency-health/requests/score
```

---

## Configuration

### Alert Webhook

Set the webhook URL when initialising the alert engine:

```python
from python_depot.dependency_health.alerts import AlertEngine
from python_depot.database import next_session

async with next_session() as db:
    engine = AlertEngine(
        db=db,
        webhook_url="https://hooks.example.com/alerts",
        severity_threshold="HIGH",  # only HIGH and CRITICAL trigger webhooks
    )
```

### Severity Thresholds

| Threshold | Webhook triggers on |
|-----------|---------------------|
| `LOW` | LOW, MEDIUM, HIGH, CRITICAL |
| `MEDIUM` (default) | MEDIUM, HIGH, CRITICAL |
| `HIGH` | HIGH, CRITICAL |
| `CRITICAL` | CRITICAL only |

---

## Dependencies

| Feature | Dependency |
|---------|------------|
| OSV.dev client (`OSVClient`) | `httpx` (included) |
| Async scanner (`DependencyScanner`) | `httpx` (included) |
| CVSS scoring | Pure Python (no deps) |
| Alert engine | `httpx` (included) |
| Safety CLI scanner (`HealthScanner`) | `safety` CLI (`pip install safety`) |

---

## Error Handling

| Status Code | Scenario |
|-------------|----------|
| `200` | Request successful |
| `404` | Package not found in scan history |
| `422` | Invalid CVSS vector or empty vuln list |
| `503` | OSV.dev API unreachable (scanner returns `unknown` status) |

---

*Dependency Health documentation for PythonDepot v0.1.0*
