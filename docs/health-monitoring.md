# Health Monitoring & Vulnerability Scanning

The Health Monitoring system provides system health checks, package vulnerability scanning, a security dashboard, CVSS scoring, and alerting.

## Overview

PythonDepot uses three layers of health monitoring:

1. **System health** — the `/health` endpoint checks database connectivity and reports uptime
2. **Package vulnerability scanning** — `DependencyScanner` (async OSV.dev API) and `HealthScanner` (safety CLI) check packages against known vulnerability databases
3. **Security dashboard** — aggregated health scores, trends, and alert management under `/api/v1/dependency-health/`

---

## System Health Check

**GET** `/health`

Returns the overall system status including database connectivity, uptime, and version.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-07-23T13:00:00Z",
  "uptime": "0d 0h 5m 30s",
  "db_status": "ok",
  "checks": {
    "database": "ok"
  }
}
```

| Field | Description |
|-------|-------------|
| `status` | `ok` when all subsystems healthy, `degraded` otherwise |
| `version` | Application version |
| `timestamp` | ISO 8601 timestamp of the check |
| `uptime` | Human-readable uptime string |
| `db_status` | Database connectivity status |
| `checks` | Per-subsystem check results (extensible) |

### Shell Command

```bash
curl http://localhost:8000/health
```

---

## Vulnerability Scanning

### List Scans

**GET** `/api/v1/vulnerabilities/{package_name}`

Lists all vulnerability scans for a package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "scans": [],
  "total": 0
}
```

Each scan (when present) includes:
```json
{
  "id": 1,
  "version": "2.31.0",
  "status": "clean",
  "vulnerability_count": 0,
  "scanned_at": "2026-07-23T13:00:00"
}
```

### Trigger Scan

**POST** `/api/v1/vulnerabilities/{package_name}/scan`

Triggers a new vulnerability scan via the `safety` CLI.

**Response:**
```json
{
  "package": "requests",
  "status": "scan_queued"
}
```

When `safety` is not installed, scans return `status: unknown` with `scanner_unavailable`.

### Get Latest Scan

**GET** `/api/v1/vulnerabilities/{package_name}/latest`

Retrieves the most recent scan result.

**Response (no scans yet):**
```json
{
  "package": "requests",
  "scan": null
}
```

**Response (with scan data):**
```json
{
  "package": "requests",
  "scan": {
    "id": 1,
    "version": "2.31.0",
    "status": "clean",
    "vulnerability_count": 0,
    "scanned_at": "2026-07-23T13:00:00"
  }
}
```

---

## Security Dashboard

Added in v0.1.0 — five REST endpoints for monitoring dependency health.

**GET** `/api/v1/dependency-health/overview`

Aggregate vulnerability statistics across all scanned packages.

```json
{
  "total_packages": 5,
  "total_scans": 42,
  "vuln_counts": {"vulnerable": 3, "clean": 37, "unknown": 2},
  "scan_coverage": 88.1,
  "last_scan": "2026-07-24T01:00:00"
}
```

---

**GET** `/api/v1/dependency-health/trends`

Vulnerability trend data over time — cumulative counts per scan.

```json
{
  "trends": [
    {"timestamp": "2026-07-23T13:00:00", "vulnerable": 0, "clean": 1, "unknown": 0, "total": 1},
    {"timestamp": "2026-07-23T14:00:00", "vulnerable": 1, "clean": 1, "unknown": 0, "total": 2}
  ]
}
```

---

**GET** `/api/v1/dependency-health/packages?sort_by=score&limit=20&offset=0`

List packages sorted by health score, with pagination.

```json
{
  "packages": [
    {"package_id": 1, "vuln_count": 0, "status": "clean", "last_scan": "2026-07-24T01:00:00"}
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

**GET** `/api/v1/dependency-health/alerts?severity=HIGH&limit=50&offset=0`

List recent vulnerability alerts, optionally filtered by severity.

```json
{
  "alerts": [
    {
      "id": 1,
      "vuln_id": "GHSA-xxxx-xxxx-xxxx",
      "severity": "CRITICAL",
      "score": 9.8,
      "webhook_status": "sent",
      "created_at": "2026-07-24T01:00:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

**GET** `/api/v1/dependency-health/{name}/score`

Composite security score for a specific package.

```json
{
  "package": "requests",
  "score": 92.5,
  "breakdown": {"base_score": 92.5, "vuln_penalty": 7.5},
  "vuln_count": 1,
  "max_severity": "MEDIUM",
  "score_label": "EXCELLENT"
}
```

| Score Label | Range |
|-------------|-------|
| EXCELLENT | 90–100 |
| GOOD | 70–89 |
| FAIR | 50–69 |
| POOR | 30–49 |
| CRITICAL | 0–29 |

---

## CVSS Scoring

The `python_depot.dependency_health.scoring` module implements CVSS v3.1 base score calculation.

```python
from python_depot.dependency_health.scoring import calculate_severity, aggregate_score

# Parse CVSS vector
result = calculate_severity("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
# → {"score": 9.8, "severity": "CRITICAL", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}

# Aggregate multiple vulnerabilities
aggregate_score([
    {"severity": "CRITICAL", "score": 9.8},
    {"severity": "HIGH", "score": 7.5},
])
# → {"total": 11.3, "max_severity": "CRITICAL", "vuln_count": 2, "avg_score": 8.65}
```

---

## AlertEngine

The `python_depot.dependency_health.alerts.AlertEngine` detects newly discovered vulnerabilities by comparing current scans against historical results.

```python
from python_depot.dependency_health.alerts import AlertEngine

engine = AlertEngine(db, webhook_url="https://hooks.example.com/alerts")

# Detect new vulns not seen in previous scans
new_vulns = engine.check_new_vulns("requests", current_scan)

# Fire webhook (respects severity threshold)
await engine.fire_webhook(alert)

# List alerts
engine.list_alerts(severity="HIGH")
```

Webhooks are delivered with this payload:

```json
{
  "event": "vulnerability_alert",
  "severity": "CRITICAL",
  "package": "requests",
  "vuln_id": "GHSA-xxxx-xxxx-xxxx",
  "score": 9.8,
  "timestamp": "2026-07-24T01:00:00Z"
}
```

Default severity threshold: `MEDIUM` (configured at `AlertEngine` construction).

---

## Scanner Services

### DependencyScanner (OSV.dev — async)

The new async scanner backed by OSV.dev API. Preferred for new integrations.

| Method | Description |
|--------|-------------|
| `scan_package(name, version)` | Scan via OSV.dev API |
| `scan_batch(packages)` | Batch query multiple packages |
| `list_scans(pkg_id, name)` | List all scans for a package |
| `latest_scan(pkg_id, name)` | Get most recent scan |

### HealthScanner (safety CLI — legacy)

Wraps the `safety` CLI for backward compatibility.

| Method | Description |
|--------|-------------|
| `scan_package(package_name, pkg_id, version)` | Run safety CLI scan |
| `list_scans(pkg_id, package_name)` | List all scans |
| `latest_scan(pkg_id, package_name)` | Get most recent scan |
| `get_compatibility(package_name, latest_version)` | Build compatibility matrix |

Both scanners persist results to the `VulnerabilityScan` model and share the same response format.

---

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def health_examples():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. System health check
        response = await client.get(f"{base_url}/health")
        health = response.json()
        print(f"Status: {health['status']}, DB: {health['db_status']}")

        # 2. List scans
        response = await client.get(f"{base_url}/api/v1/vulnerabilities/requests")
        scans = response.json()
        print(f"Previous scans: {scans['total']}")

        # 3. Trigger a scan
        response = await client.post(f"{base_url}/api/v1/vulnerabilities/requests/scan")
        print(f"Scan status: {response.json()['status']}")

        # 4. Get latest scan
        response = await client.get(f"{base_url}/api/v1/vulnerabilities/requests/latest")
        latest = response.json()
        print(f"Latest scan: {latest['scan']}")

        # 5. Dashboard overview
        response = await client.get(f"{base_url}/api/v1/dependency-health/overview")
        overview = response.json()
        print(f"Dashboard: {overview['total_packages']} packages, {overview['scan_coverage']}% coverage")

        # 6. Package health score
        response = await client.get(f"{base_url}/api/v1/dependency-health/requests/score")
        score = response.json()
        print(f"Package score: {score['score']} ({score['score_label']})")

asyncio.run(health_examples())
```

### Shell Commands

```bash
# System health
curl http://localhost:8000/health

# List scans
curl http://localhost:8000/api/v1/vulnerabilities/requests

# Trigger scan
curl -X POST http://localhost:8000/api/v1/vulnerabilities/requests/scan

# Get latest scan
curl http://localhost:8000/api/v1/vulnerabilities/requests/latest

# Dashboard overview
curl http://localhost:8000/api/v1/dependency-health/overview

# Trend data
curl http://localhost:8000/api/v1/dependency-health/trends

# Package health score
curl http://localhost:8000/api/v1/dependency-health/requests/score

# Recent alerts
curl http://localhost:8000/api/v1/dependency-health/alerts

# Filter by severity
curl "http://localhost:8000/api/v1/dependency-health/alerts?severity=HIGH"
```

---

## Dependencies

The vulnerability scanner supports two backends:

| Engine | Requires | Source |
|--------|----------|--------|
| `DependencyScanner` | `httpx` (bundled) | OSV.dev API (no install needed) |
| `HealthScanner` | `safety` CLI | `pip install safety` |

Without `safety`, the legacy HealthScanner returns `status: "unknown"` with `scanner_unavailable` details.

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found in scan history |
| `422` | Invalid CVSS vector or empty vulnerability list |

---

*Health Monitoring documentation for PythonDepot v0.1.0*
