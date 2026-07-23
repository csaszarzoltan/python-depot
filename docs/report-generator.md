# Report Generator

The Report Generator provides monthly "Best of PythonDepot" reports with JSON and HTML output formats.

## Endpoints

### List Reports

**GET** `/api/v1/reports/`

Lists available monthly reports, optionally filtered by year.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Filter by year (optional) |

**Response:**
```json
{
  "reports": [],
  "year": null
}
```

### Generate Report

**POST** `/api/v1/reports/generate`

Triggers generation of a monthly report. Requires year and month query parameters.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Year (required) |
| `month` | integer | Month 1-12 (required) |

**Response:**
```json
{
  "year": 2026,
  "month": 7,
  "status": "generated"
}
```

### Get Report (JSON)

**GET** `/api/v1/reports/{year}/{month}`

Retrieves a specific monthly report in JSON format.

**Path Parameters:**
- `year` (integer, required): Report year
- `month` (integer, required): Report month (1-12)

**Response:**
```json
{
  "year": 2026,
  "month": 7,
  "report": null
}
```

### Get Report (HTML)

**GET** `/api/v1/reports/{year}/{month}/html`

Retrieves a specific monthly report rendered as an HTML page.

**Path Parameters:**
- `year` (integer, required): Report year
- `month` (integer, required): Report month (1-12)

**Response:** `text/html`

```html
<html><body><h1>Report 2026/07</h1><p>No data yet.</p></body></html>
```

---

## ReportService

The `python_depot.pydepot.reports.ReportService` class provides the report generation logic:

| Method | Description |
|--------|-------------|
| `generate_monthly_report(year, month)` | Generate a monthly "Best of PythonDepot" report |
| `get_report(year, month)` | Retrieve a previously generated report |
| `list_reports(year)` | List available reports, filtered by year |

Reports are rendered using Jinja2 templates (see `src/templates/report.html`).

---

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def report_examples():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. List reports
        response = await client.get(f"{base_url}/api/v1/reports/")
        data = response.json()
        print(f"Available reports: {data}")

        # 2. Generate a report
        response = await client.post(
            f"{base_url}/api/v1/reports/generate",
            params={"year": 2026, "month": 7}
        )
        print(f"Generated: {response.json()['status']}")

        # 3. Get report JSON
        response = await client.get(f"{base_url}/api/v1/reports/2026/7")
        print(f"Report data: {response.json()}")

        # 4. Get report HTML
        response = await client.get(f"{base_url}/api/v1/reports/2026/7/html")
        print(f"HTML length: {len(response.text)} chars")

asyncio.run(report_examples())
```

### Shell Commands

```bash
# List reports
curl "http://localhost:8000/api/v1/reports/"
curl "http://localhost:8000/api/v1/reports/?year=2026"

# Generate a report for July 2026
curl -X POST "http://localhost:8000/api/v1/reports/generate?year=2026&month=7"

# Get report as JSON
curl http://localhost:8000/api/v1/reports/2026/7

# Get report as HTML
curl http://localhost:8000/api/v1/reports/2026/7/html
```

---

## Models

### Report

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier |
| `year` | integer | Report year |
| `month` | integer | Report month (1-12) |
| `generated_at` | datetime | When the report was generated |
| `data_json` | text | Report content (JSON) |

### MonthlyReport (DB Model)

Unique constraint on `(year, month)` — only one report per month.

---

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Report not found for given year/month |
| `422` | Missing or invalid year/month parameters |

---
*Report Generator documentation for PythonDepot*
