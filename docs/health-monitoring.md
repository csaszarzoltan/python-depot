# Health Monitoring & Vulnerability Scanning

The Health Monitoring system provides system health checks, package vulnerability scanning, and dependency compatibility assessment.

## Overview

PythonDepot uses two layers of health monitoring:

1. **System health** — the `/health` endpoint checks database connectivity and reports uptime
2. **Package vulnerability scanning** — the `HealthScanner` class integrates with the `safety` CLI to check packages against known CVE databases

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

## HealthScanner Service

The `python_depot.dependency_health.scanner.HealthScanner` class provides the core scanning logic:

| Method | Description |
|--------|-------------|
| `scan_package(package_name, pkg_id, version)` | Run safety CLI scan and persist result |
| `list_scans(pkg_id, package_name)` | List all scans for a package |
| `latest_scan(pkg_id, package_name)` | Get most recent scan |
| `get_compatibility(package_name, latest_version)` | Build compatibility matrix |

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
```

---

## Dependencies

The vulnerability scanner requires the `safety` CLI:

```bash
pip install safety
```

Without `safety`, scans return `status: "unknown"` and `scanner_unavailable` details.

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found in scan history |

---
*Health Monitoring documentation for PythonDepot*
