# Dependency Health Module

OSV.dev-backed dependency vulnerability scanner, alert engine, and CVSS v3.1 scoring — monitoring dependency health over time with real-time alerts.

## Architecture

```
python_depot/dependency_health/
├── __init__.py               # Module exports
├── models.py                 # VulnerabilityScan, VulnerabilityAlert (SQLAlchemy)
├── osv_client.py             # Async OSV.dev API client
├── scanner.py                # DependencyScanner (async OSV) + HealthScanner (safety CLI)
├── scoring.py                # CVSS v3.1 calculator + aggregate scoring
└── alerts.py                 # AlertEngine — new-vuln detection + webhook delivery
```

## OSVClient

Async HTTP client for the [OSV.dev](https://osv.dev) open-source vulnerability database.

```python
from python_depot.dependency_health.osv_client import OSVClient

client = OSVClient()

# Query a specific package version
result = await client.query_package("requests", "2.31.0")
# → {"vulns": [{"id": "GHSA-xxxx-xxxx-xxxx", ...}]}

# Batch query multiple packages at once
results = await client.query_batch([
    {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.31.0"},
    {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "2.3.0"},
])
# → [{"results": [...]}, {"results": [...]}]

# Fetch full vulnerability details
details = await client.get_vuln_details("GHSA-xxxx-xxxx-xxxx")
# → {"id": "GHSA-...", "summary": "...", "aliases": ["CVE-2024-..."], "severity": [...]}
```

### Methods

| Method | Description |
|--------|-------------|
| `query_package(name, version=None)` | Query OSV.dev for a single package |
| `query_batch(queries)` | Batch query multiple packages |
| `get_vuln_details(vuln_id)` | Full vulnerability details |

## DependencyScanner

Async scanner wrapping `OSVClient` with scan persistence and history.

```python
from sqlalchemy.orm import Session
from python_depot.dependency_health.scanner import DependencyScanner

scanner = DependencyScanner(db)

# Scan a single package
result = await scanner.scan_package("requests", "2.31.0")
# → {"package": "requests", "version": "2.31.0", "status": "clean", "scan_id": 1}

# Scan multiple packages
results = await scanner.scan_batch([
    {"name": "requests", "version": "2.31.0"},
    {"name": "flask", "version": "2.3.0"},
])

# List scan history
scanner.list_scans(pkg_id=1, name="requests")

# Get latest scan
scanner.latest_scan(pkg_id=1, name="requests")
```

### Methods

| Method | Description |
|--------|-------------|
| `scan_package(name, version=None)` | Scan a package via OSV.dev API |
| `scan_batch(packages)` | Batch scan multiple packages |
| `list_scans(pkg_id, name)` | List scan history for a package |
| `latest_scan(pkg_id, name)` | Get most recent scan result |

### Return Values

| `status` | Meaning |
|----------|---------|
| `clean` | No vulnerabilities found |
| `vulnerable` | One or more vulnerabilities detected |
| `unknown` | Scan failed (network error, API unavailable) |

## AlertEngine

Compares current scan results against previous scans to detect newly discovered vulnerabilities and delivers webhook notifications.

```python
from python_depot.dependency_health.alerts import AlertEngine

engine = AlertEngine(
    db,
    webhook_url="https://hooks.example.com/alerts",
    severity_threshold="HIGH",  # Only fire webhooks for HIGH and CRITICAL
)

# Check for new vulnerabilities vs previous scan
new_vulns = engine.check_new_vulns("requests", current_scan)
# → [{"vuln_id": "GHSA-xxxx", "severity": "CRITICAL", ...}]

# Fire webhook for an alert
success = await engine.fire_webhook(alert)
# → True if delivered, False if below threshold or delivery failed

# List alert history
alerts = engine.list_alerts(severity="HIGH")
# → [{"id": 1, "vuln_id": "...", "severity": "HIGH", "webhook_status": "sent", ...}]
```

### Severity Thresholds

| Threshold | Triggers webhook for |
|-----------|---------------------|
| `LOW` | All alerts (LOW, MEDIUM, HIGH, CRITICAL) |
| `MEDIUM` | MEDIUM, HIGH, CRITICAL (default) |
| `HIGH` | HIGH, CRITICAL only |
| `CRITICAL` | CRITICAL only |

### Webhook Payload

```json
{
  "event": "vulnerability_alert",
  "severity": "CRITICAL",
  "package": "requests",
  "vuln_id": "GHSA-xxxx-xxxx-xxxx",
  "score": 9.8,
  "timestamp": "2026-07-24T01:00:00Z",
  "details": "{\"id\": \"GHSA-xxxx\", ...}"
}
```

## CVSS Scoring Engine

Implements the CVSS v3.1 base score formula as published by FIRST.org.

```python
from python_depot.dependency_health.scoring import calculate_severity, aggregate_score

# Parse a CVSS vector string
result = calculate_severity("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
# → {"score": 9.8, "severity": "CRITICAL", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}

# Aggregate multiple vulnerabilities into a composite health score
aggregate_score([
    {"severity": "CRITICAL", "score": 9.8},
    {"severity": "HIGH", "score": 7.5},
])
# → {"total": 11.3, "max_severity": "CRITICAL", "vuln_count": 2, ...}
```

### `calculate_severity(vector)`

Parses a CVSS v3.1 vector string and returns:

| Field | Description |
|-------|-------------|
| `score` | Base score 0.0–10.0 |
| `severity` | NONE, LOW, MEDIUM, HIGH, or CRITICAL |
| `vector` | Original vector string |

Raises `ValueError` for malformed vectors.

### `aggregate_score(vulns)`

Aggregates multiple vulnerability scores into a package health score:

| Field | Description |
|-------|-------------|
| `total` | Composite score 0.0–10.0 (higher = worse) |
| `max_severity` | Highest severity found |
| `vuln_count` | Number of vulnerabilities evaluated |
| `avg_score` | Average CVSS base score |
| `breakdown` | Per-severity counts |

Raises `ValueError` for empty input or invalid severity labels.

## Security Dashboard API

Added under the `/api/v1/dependency-health/` prefix — five endpoints for monitoring dependency health over time.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dependency-health/overview` | Aggregate vulnerability stats across all packages |
| GET | `/api/v1/dependency-health/trends` | Vulnerability trend data over time |
| GET | `/api/v1/dependency-health/packages` | Packages sorted by health score |
| GET | `/api/v1/dependency-health/alerts` | Recent vulnerability alerts |
| GET | `/api/v1/dependency-health/{name}/score` | Composite security score for a package |

### Overview Response

```json
{
  "total_packages": 5,
  "total_scans": 42,
  "vuln_counts": {"vulnerable": 3, "clean": 37, "unknown": 2},
  "scan_coverage": 88.1,
  "last_scan": "2026-07-24T01:00:00"
}
```

### Package Score Response

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

## Database Models

### `VulnerabilityScan`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `package_id` | Integer (FK) | References `packages.id` |
| `version` | String | Scanned version |
| `scanner` | String | `safety` or `osv` |
| `status` | String | `clean`, `vulnerable`, or `unknown` |
| `vuln_count` | Integer | Number of vulnerabilities |
| `details` | Text | JSON vulnerability list |
| `scanned_at` | DateTime | Scan timestamp |

### `VulnerabilityAlert`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `package_id` | Integer (FK) | References `packages.id` |
| `vuln_id` | String | OSV vulnerability ID |
| `severity` | String | CRITICAL, HIGH, MEDIUM, LOW |
| `score` | Float | CVSS score |
| `details` | Text | Full vulnerability JSON |
| `webhook_status` | String | `pending`, `sent`, `failed` |
| `created_at` | DateTime | Alert timestamp |

## Backward Compatibility

The legacy `HealthScanner` class remains available for projects that depend on the `safety` CLI. It shares the same `VulnerabilityScan` model and response format as `DependencyScanner`.

```
HealthScanner → safety CLI → VulnerabilityScan model
DependencyScanner → OSV.dev API → VulnerabilityScan model
```

Both can coexist — call `DependencyScanner` for OSV.dev queries and `HealthScanner` for safety CLI fallback.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| OSV.dev API returns 404 | `get_vuln_details` raises `httpx.HTTPStatusError` |
| OSV.dev network timeout | `scan_package` returns `status: "unknown"` |
| safety CLI not installed | `scan_package` returns `status: "unknown"`, details: `scanner_unavailable` |
| Invalid CVSS vector | `calculate_severity` raises `ValueError` with parse error |
| Empty vuln list for aggregate | `aggregate_score` raises `ValueError` |

## Dependencies

- `httpx` — async HTTP client for OSV.dev API
- `sqlalchemy` — database ORM for scan persistence
- `safety` (optional) — CLI-based vulnerability scanner fallback

---

*Dependency Health documentation for PythonDepot v0.1.0*
