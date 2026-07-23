# Health Monitoring

The Health Monitoring system provides comprehensive package dependency checking and vulnerability scanning for the PythonDepot platform.

## Overview

Health monitoring includes:
- Package dependency analysis
- Vulnerability scanning
- Version compatibility checks
- Health status reporting
- Automated monitoring and alerts

## Features

### Package Health

- Dependency tree analysis
- Missing dependency detection
- Version conflict resolution
- Compatibility scoring

### Vulnerability Scanning

- Security vulnerability database integration
- CVE tracking and alerts
- Severity assessment
- Remediation recommendations

### Monitoring Dashboard

- Real-time health status
- Historical vulnerability trends
- Package health scores
- Automated alerts

## Endpoints

### List Scans

**GET** `/api/v1/vulnerabilities/{package_name}`

Retrieves all vulnerability scans for a specific package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "scans": [
    {
      "id": 1,
      "scan_type": "vulnerability",
      "severity": "high",
      "cve_ids": ["CVE-2021-12345"],
      "affected_versions": ["<2.25.0"],
      "fixed_in": "2.25.1",
      "discovered_at": "2024-01-15T10:30:00Z",
      "status": "active"
    }
  ],
  "total": 1
}
```

### Trigger Scan

**POST** `/api/v1/vulnerabilities/{package_name}/scan`

Initiates a new vulnerability scan for the specified package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Request Body:**
```json
{
  "scan_type": "vulnerability",
  "intensity": "full",
  "sources": ["nvd", "ghsa", "osv"],
  "exclude_known": true,
  "notes": "Scheduled weekly scan"
}
```

**Response:**
```json
{
  "package": "requests",
  "status": "scan_queued",
  "scan_id": "scan_20240115_001",
  "estimated_completion": "2024-01-15T11:00:00Z"
}
```

### Get Latest Scan

**GET** `/api/v1/vulnerabilities/{package_name}/latest`

Retrieves the most recent vulnerability scan result.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "scan": {
    "id": 1,
    "scan_type": "vulnerability",
    "severity": "medium",
    "cve_ids": ["CVE-2021-12345"],
    "affected_versions": ["<2.20.0"],
    "fixed_in": "2.20.1",
    "discovered_at": "2024-01-15T10:30:00Z",
    "status": "fixed",
    "recommendations": [
      "Update to version 2.20.1 or later",
      "Review dependency chain",
      "Consider alternative packages if critical"
    ]
  }
}
```

## Health Check Endpoint

**GET** `/health`

Returns the overall system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:45:00Z",
  "services": {
    "database": "operational",
    "api": "operational",
    "scanner": "operational"
  },
  "version": "0.1.0"
}
```

## Models

### Scan Result

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique scan identifier |
| `package` | string | Package name |
| `scan_type` | string | Type of scan (vulnerability, dependency, license) |
| `severity` | string | Severity level (low, medium, high, critical) |
| `cve_ids` | array | List of CVE identifiers |
| `affected_versions` | array | Package versions affected |
| `fixed_in` | string | Version where vulnerability is fixed |
| `discovered_at` | datetime | When vulnerability was discovered |
| `status` | string | Current status (active, fixed, monitored) |
| `recommendations` | array | Remediation recommendations |

### Scan Request

| Field | Type | Description |
|-------|------|-------------|
| `scan_type` | string | Type of scan to perform |
| `intensity` | string | Scan intensity (light, medium, full) |
| `sources` | array | Vulnerability data sources |
| `exclude_known` | boolean | Whether to exclude known vulnerabilities |
| `notes` | string | Optional notes about the scan |

## Example Usage

### Python Client

```python
import httpx
import asyncio
import json
from typing import Dict, List

async def health_examples():
    base_url = "http://localhost:8000"
    
    # 1. Check system health
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        health_data = response.json()
        print(f"System status: {health_data['status']}")
        print(f"Services operational: {health_data['services']}")
        
        # 2. List vulnerability scans for a package
        response = await client.get(f"{base_url}/api/v1/vulnerabilities/requests")
        scans = response.json()
        print(f"Scans found: {scans['total']}")
        
        # 3. Trigger a new vulnerability scan
        scan_request = {
            "scan_type": "vulnerability",
            "intensity": "full",
            "sources": ["nvd", "ghsa"],
            "exclude_known": True
        }
        response = await client.post(
            f"{base_url}/api/v1/vulnerabilities/requests/scan",
            json=scan_request
        )
        scan_result = response.json()
        print(f"Scan queued: {scan_result['status']}")
        print(f"Estimated completion: {scan_result['estimated_completion']}")
        
        # 4. Get latest scan results
        response = await client.get(f"{base_url}/api/v1/vulnerabilities/requests/latest")
        latest_scan = response.json()
        if latest_scan['scan']:
            scan = latest_scan['scan']
            print(f"Latest severity: {scan['severity']}")
            print(f"Status: {scan['status']}")
            print(f"CVEs: {', '.join(scan['cve_ids'])}")

# Run the examples
asyncio.run(health_examples())
```

### Shell Commands

```bash
# Check system health
curl http://localhost:8000/health

# List vulnerability scans
curl http://localhost:8000/api/v1/vulnerabilities/requests

# Trigger new scan
curl -X POST http://localhost:8000/api/v1/vulnerabilities/requests/scan \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "vulnerability",
    "intensity": "full",
    "sources": ["nvd", "ghsa"],
    "exclude_known": true
  }'

# Get latest scan results
curl http://localhost:8000/api/v1/vulnerabilities/requests/latest
```

## Testing

```bash
# Run vulnerability-specific tests
pytest tests/test_vulnerabilities.py -v

# Test vulnerability scanning
pytest tests/test_vulnerabilities.py::test_list_scans_returns_empty -v

# Test vulnerability triggering
pytest tests/test_vulnerabilities.py::test_trigger_scan -v
```

## Error Handling

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found |
| `400` | Invalid scan request |
| `409` | Scan already in progress |

### Example Error Response

```json
{
  "detail": "Package 'nonexistent' not found in catalog or scan history"
}
```

## Monitoring & Alerting

The health monitoring system includes:

1. **Automated Scans**: Scheduled vulnerability scans via cron jobs or monitoring services
2. **Alert Integration**: Notifications sent via email, Slack, or webhook
3. **Dashboard**: Real-time monitoring dashboard with historical trends
4. **Reporting**: Automated security reports

### Example Cron Job for Automated Scanning

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * /usr/local/bin/python -m health_monitor.scan_scheduler

# Or via systemd service
[Unit]
Description=PythonDepot Health Monitor
After=docker.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/python -m health_monitor.scan_scheduler
User=app-user

[Install]
WantedBy=multi-user.target
```

## Integration with Other APIs

The Health API integrates with:

1. **Catalog API**: Provides package information for scanning
2. **Analytics API**: Tracks scan results and trends
3. **Ratings API**: Notifies users of security concerns affecting ratings

## Security Considerations

1. **Rate Limiting**: Vulnerability scans are limited to 1 per hour per package
2. **Resource Management**: Scans use controlled resources to prevent abuse
3. **Data Privacy**: Scan results do not include internal network information
4. **Logging**: All scans are logged for audit and compliance

---
*Health Monitoring documentation for PythonDepot*