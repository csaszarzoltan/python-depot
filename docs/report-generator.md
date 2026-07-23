# Report Generator

The Report Generator provides comprehensive report functionality for the PythonDepot platform, including package analytics, health reports, and custom report generation.

## Overview

The report generator system includes:
- Automated report scheduling
- Multiple report formats (JSON, CSV, HTML)
- Custom report templates
- Email delivery integration
- Scheduled report distribution

## Features

### Report Types

1. **Package Analytics Report**
   - Package usage statistics
   - Trending analysis
   - Rating distributions
   - Version popularity

2. **Health Monitor Report**
   - System health status
   - Security scan results
   - Package vulnerability summary
   - Compliance metrics

3. **Usage Pattern Report**
   - User behavior analytics
   - Search patterns
   - Package interaction trends
   - Session metrics

4. **Custom Report**
   - User-defined report templates
   - Time-range filtering
   - Metric selection
   - Export format selection

### Report Formats

- **JSON**: Machine-readable format
- **CSV**: Spreadsheet-compatible
- **HTML**: Human-readable with embedded charts
- **PDF**: Formatted documents

### Delivery Methods

- **Email**: Automated scheduled delivery
- **API**: On-demand report generation
- **File System**: Local file export
- **Webhook**: External system integration

## Features

### Package Analytics Report

Generates comprehensive package usage and performance reports.

**Key Metrics:**
- Total views and downloads
- Package growth trends
- Rating distributions
- Version adoption patterns
- Top packages by category

**Example Output:**
```json
{
  "report_type": "package_analytics",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-15"
  },
  "summary": {
    "total_packages": 500,
    "total_views": 1500000,
    "total_downloads": 500000,
    "average_rating": 4.2
  },
  "top_packages": [
    {
      "package": "requests",
      "downloads": 1500000,
      "growth_rate": 5.2,
      "rating": 4.5
    }
  ],
  "categories": {
    "web-framework": 150,
    "data-science": 120,
    "developer-tools": 80
  }
}
```

### Health Monitor Report

Generates security and system health reports.

**Key Metrics:**
- Package vulnerability summary
- Security scan status
- Fix compliance rate
- Critical issue count
- Health endpoint performance

**Example Output:**
```json
{
  "report_type": "health_monitor",
  "scan_date": "2024-01-15",
  "summary": {
    "total_packages_scanned": 500,
    "critical_vulnerabilities": 5,
    "high_vulnerabilities": 25,
    "medium_vulnerabilities": 50,
    "low_vulnerabilities": 100,
    "compliance_rate": 98.5
  },
  "package_status": {
    "requests": {
      "vulnerabilities": 0,
      "scan_status": "clean",
      "last_scan": "2024-01-14T10:30:00Z"
    }
  }
}
```

### Usage Pattern Report

Generates user behavior and interaction reports.

**Key Metrics:**
- Active user count
- Peak usage times
- Popular search terms
- Package interaction frequency
- Session duration averages

**Example Output:**
```json
{
  "report_type": "usage_pattern",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-15"
  },
  "user_metrics": {
    "total_users": 10000,
    "active_users": 2500,
    "average_sessions_per_user": 3.5,
    "average_session_duration": 120
  },
  "search_analysis": {
    "top_searches": ["requests", "django", "flask"],
    "search_trends": ["package_view", "package_download", "package_rate"]
  },
  "interaction_patterns": {
    "most_viewed_packages": ["requests", "django", "flask"],
    "most_downloaded_packages": ["requests", "numpy", "pandas"]
  }
}
```

## API Endpoints

### Generate Package Analytics Report

**POST** `/api/v1/reports/package-analytics`

Generates a package analytics report.

**Request Body:**
```json
{
  "report_type": "package_analytics",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-15"
  },
  "format": "json",
  "include_categories": true,
  "include_trends": true,
  "top_n": 10,
  "email_recipients": ["admin@example.com"],
  "schedule": {
    "type": "daily",
    "time": "09:00"
  }
}
```

**Response:**
```json
{
  "report_id": "report_20240115_001",
  "status": "scheduled",
  "estimated_completion": "2024-01-15T10:00:00Z",
  "download_url": "https://api.example.com/reports/download/report_20240115_001.json"
}
```

### Generate Health Monitor Report

**POST** `/api/v1/reports/health-monitor`

Generates a health monitoring report.

**Request Body:**
```json
{
  "report_type": "health_monitor",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-15"
  },
  "format": "json",
  "include_vulnerabilities": true,
  "include_system_health": true,
  "severity_filter": "all",
  "email_recipients": ["security@example.com"],
  "schedule": {
    "type": "daily",
    "time": "02:00"
  }
}
```

**Response:**
```json
{
  "report_id": "health_report_20240115_001",
  "status": "scheduled",
  "estimated_completion": "2024-01-15T03:00:00Z",
  "download_url": "https://api.example.com/reports/download/health_report_20240115_001.json"
}
```

### Download Report

**GET** `/api/v1/reports/download/{report_id}`

Downloads a generated report.

**Path Parameters:**
- `report_id` (string, required): Report identifier

**Query Parameters:**
- `format` (string, optional): Output format (json, csv, html)

**Response:**
- JSON file, CSV file, or HTML page depending on format

### Get Report Status

**GET** `/api/v1/reports/status/{report_id}`

Checks the status of a report generation job.

**Path Parameters:**
- `report_id` (string, required): Report identifier

**Response:**
```json
{
  "report_id": "report_20240115_001",
  "status": "completed",
  "progress": 100,
  "download_url": "https://api.example.com/reports/download/report_20240115_001.json",
  "completed_at": "2024-01-15T10:05:00Z",
  "error": null
}
```

## Models

### Report Request

| Field | Type | Description |
|-------|------|-------------|
| `report_type` | string | Type of report (package_analytics, health_monitor, usage_pattern, custom) |
| `date_range` | object | Start and end dates |
| `format` | string | Output format (json, csv, html) |
| `include_categories` | boolean | Whether to include category breakdown |
| `include_trends` | boolean | Whether to include trend analysis |
| `top_n` | integer | Number of top items to include |
| `email_recipients` | array | Email addresses for delivery |
| `schedule` | object | Scheduling configuration |

### Report Response

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | string | Unique report identifier |
| `status` | string | Report status (pending, scheduled, processing, completed, failed) |
| `estimated_completion` | datetime | Estimated completion time |
| `download_url` | string | URL to download the report |

## Example Usage

### Python Client

```python
import httpx
import asyncio
import json
from typing import Dict, List
from datetime import datetime, timedelta

async def report_examples():
    base_url = "http://localhost:8000"
    
    # 1. Generate package analytics report
    async with httpx.AsyncClient() as client:
        analytics_request = {
            "report_type": "package_analytics",
            "date_range": {
                "start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            },
            "format": "json",
            "include_categories": True,
            "include_trends": True,
            "top_n": 10,
            "email_recipients": ["admin@example.com"],
            "schedule": {
                "type": "daily",
                "time": "09:00"
            }
        }
        
        response = await client.post(
            f"{base_url}/api/v1/reports/package-analytics",
            json=analytics_request
        )
        analytics_result = response.json()
        print(f"Package analytics report ID: {analytics_result['report_id']}")
        print(f"Status: {analytics_result['status']}")
        print(f"Estimated completion: {analytics_result['estimated_completion']}")
        
        # 2. Generate health monitor report
        health_request = {
            "report_type": "health_monitor",
            "date_range": {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            },
            "format": "json",
            "include_vulnerabilities": True,
            "include_system_health": True,
            "severity_filter": "high",
            "email_recipients": ["security@example.com"]
        }
        
        response = await client.post(
            f"{base_url}/api/v1/reports/health-monitor",
            json=health_request
        )
        health_result = response.json()
        print(f"\nHealth monitor report ID: {health_result['report_id']}")
        print(f"Status: {health_result['status']}")
        
        # 3. Check report status
        response = await client.get(f"{base_url}/api/v1/reports/status/{analytics_result['report_id']}")
        status = response.json()
        print(f"\nReport status: {status['status']}")
        
        if status['status'] == 'completed':
            print(f"Download URL: {status['download_url']}")

# Run the examples
asyncio.run(report_examples())
```

### Shell Commands

```bash
# Generate package analytics report
curl -X POST http://localhost:8000/api/v1/reports/package-analytics \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "package_analytics",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-15"
    },
    "format": "json",
    "include_categories": true,
    "include_trends": true,
    "top_n": 10,
    "email_recipients": ["admin@example.com"],
    "schedule": {
      "type": "daily",
      "time": "09:00"
    }
  }'

# Generate health monitor report
curl -X POST http://localhost:8000/api/v1/reports/health-monitor \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "health_monitor",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-15"
    },
    "format": "json",
    "include_vulnerabilities": true,
    "include_system_health": true,
    "severity_filter": "high",
    "email_recipients": ["security@example.com"]
  }'

# Download completed report
curl http://localhost:8000/api/v1/reports/download/report_20240115_001.json

# Check report status
curl http://localhost:8000/api/v1/reports/status/report_20240115_001
```

## Testing

```bash
# Test report generation endpoints (if implemented)
# pytest tests/test_reports.py -v  # Assuming report tests exist

# Test individual report types
# pytest tests/test_reports.py::test_package_analytics_report -v
# pytest tests/test_reports.py::test_health_monitor_report -v
```

## Report Scheduling

Reports can be scheduled for automatic generation and delivery:

### Cron Job Configuration

```bash
# Daily package analytics at 9 AM
0 9 * * * /usr/local/bin/python -m reports.schedule.package_analytics

# Weekly health monitor on Sunday at 2 AM
0 2 * * 0 /usr/local/bin/python -m reports.schedule.health_monitor

# Monthly custom report on the 1st at 8 AM
0 8 1 * * /usr/local/bin/python -m reports.schedule.custom
```

### Schedule Formats

- **daily**: Runs once per day
- **weekly**: Runs once per week (Sunday)
- **monthly**: Runs once per month (1st day)
- **on_demand**: Runs immediately when triggered

## Report Templates

### JSON Template
```json
{
  "report_metadata": {
    "report_id": "{report_id}",
    "generated_at": "{timestamp}",
    "report_type": "{report_type}",
    "date_range": "{date_range}"
  },
  "executive_summary": "...",
  "detailed_metrics": "...",
  "appendices": "..."
}
```

### CSV Template
```csv
package_name,total_downloads,growth_rate,average_rating,downloads_7d
requests,1500000,5.2,4.5,12000
django,800000,3.1,4.2,8000
flask,450000,8.7,4.7,3000
```

### HTML Template
```html
<!DOCTYPE html>
<html>
<head><title>{report_title}</title></head>
<body>
<h1>{report_title}</h1>
<p>Generated: {timestamp}</p>
{charts_and_tables}
</body>
</html>
```

## Integration with Other APIs

The Report Generator integrates with:

1. **Catalog API**: Retrieves package metadata for reports
2. **Analytics API**: Consumes analytics data for report content
3. **Health API**: Includes security and system health data
4. **Ratings API**: Incorporates rating data in reports

## Email Integration

The report generator can automatically email reports to recipients:

### SMTP Configuration

```python
# config/email.py
EMAIL_CONFIG = {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "reports@example.com",
    "password": "secure_password",
    "from_email": "reports@example.com",
    "use_tls": True,
    "bcc_admin": True
}
```

### Email Template

```html
Subject: Daily Package Analytics Report - {{ date }}

Dear {{ recipient_name }},

Please find attached today's package analytics report.

Key Highlights:
- Top packages by downloads: {{ top_packages }}
- New packages added: {{ new_packages_count }}
- System health: {{ health_status }}

Best regards,
PythonDepot Analytics Team
```

## Configuration

### Report Generator Settings

```python
# config/reports.py
REPORT_CONFIG = {
    "max_report_size_mb": 10,
    "report_retention_days": 90,
    "email_batch_size": 50,
    "supported_formats": ["json", "csv", "html"],
    "report_types": ["package_analytics", "health_monitor", "usage_pattern"],
    "default_schedule": {
        "package_analytics": "daily 09:00",
        "health_monitor": "daily 02:00",
        "usage_pattern": "weekly sunday 08:00"
    }
}
```

## Performance Optimization

1. **Caching**: Cache report data for 1-4 hours
2. **Incremental Reports**: Generate incremental updates for daily reports
3. **Lazy Loading**: Defer expensive queries until needed
4. **Compression**: Compress large reports before delivery
5. **Parallel Processing**: Process multiple packages concurrently

## Error Handling

### Common Error Scenarios

1. **Invalid Date Range**: Report must cover valid date range
2. **Email Delivery Failure**: Retry with exponential backoff
3. **Memory Exhaustion**: Split large reports into chunks
4. **Database Timeout**: Implement retry logic with circuit breaker

### Error Response Format

```json
{
  "error": {
    "code": "REPORT_GENERATION_FAILED",
    "message": "Unable to generate report due to database timeout",
    "details": "Please try again in a few minutes",
    "report_id": null
  }
}
```

## Monitoring & Logging

Report generation includes comprehensive logging:

```python
import logging

logger = logging.getLogger(__name__)

# Log report generation
logger.info(f"Starting report generation: {report_id}")

# Log progress
logger.info(f"Report progress: {progress}% - {current_package}")

# Log completion
logger.info(f"Report completed: {report_id} - Size: {file_size} bytes")

# Log errors
logger.error(f"Report generation failed: {report_id} - {error}", exc_info=True)
```

---
*Report Generator documentation for PythonDepot*"