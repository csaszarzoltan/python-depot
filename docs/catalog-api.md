# Catalog API

The Catalog API provides package discovery, CRUD management, full-text search, and time-series trends for Python packages.

## Endpoints

### List All Packages

**GET** `/api/v1/packages/`

Returns an empty list by default (packages are populated via the PyPI catalog service or direct creation).

**Response:**
```json
{
  "packages": [],
  "total": 0
}
```

### Get Package Health Report

**GET** `/api/v1/packages/{package_name}`

Returns a synthetic health report for a package. Package names must match `[a-zA-Z0-9][a-zA-Z0-9._-]*` (PEP 508 compliant). Invalid names return `422`.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response (valid name, found):**
```json
{
  "name": "requests",
  "health_score": 85,
  "latest_version": "1.0.0",
  "dependency_status": "up-to-date",
  "vulnerability_count": 0
}
```

**Response (not found — 404):**
```json
{
  "found": false,
  "name": "nonexistent-package"
}
```

### Search Packages

**GET** `/api/v1/packages/search`

Full-text search with pagination. Requires the `q` parameter (returns `422` if missing).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query |
| `page` | integer | 1 | Page number (≥1) |
| `page_size` | integer | 20 | Results per page (1–100) |

**Response:**
```json
{
  "results": [
    {
      "name": "requests",
      "summary": "Packages matching 'requests'",
      "score": 1.0
    }
  ],
  "total": 1,
  "query": "requests"
}
```

### Get Package Trends

**GET** `/api/v1/packages/{package_name}/trends`

Returns daily download and star count time-series data for a package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | `30d` | One of `7d`, `30d`, `90d` |

**Response:**
```json
{
  "name": "requests",
  "trends": [
    {"date": "2026-06-23", "downloads": 100, "stars": 10},
    {"date": "2026-06-24", "downloads": 101, "stars": 11}
  ],
  "period": "30d"
}
```

### Create Package

**POST** `/api/v1/packages/`

Registers a new package in the catalog.

**Request Body:**
```json
{
  "name": "new-package",
  "summary": "A new package",
  "description": "Description of the new package",
  "homepage": "https://example.com",
  "repository": "https://github.com/user/new-package",
  "author": "Package Author",
  "license": "MIT",
  "latest_version": "1.0.0"
}
```

**Response:**
```json
{
  "status": "created"
}
```

### Update Package

**PUT** `/api/v1/packages/{package_name}`

Updates an existing package's metadata.

**Request Body:**
```json
{
  "summary": "Updated summary",
  "latest_version": "1.1.0"
}
```

**Response:**
```json
{
  "name": "new-package",
  "status": "updated"
}
```

### Delete Package

**DELETE** `/api/v1/packages/{package_name}`

Removes a package from the catalog.

**Response:**
```json
{
  "name": "new-package",
  "status": "deleted"
}
```

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def catalog_examples():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. List all packages
        response = await client.get(f"{base_url}/api/v1/packages/")
        print(f"Total packages: {response.json()['total']}")

        # 2. Search packages
        response = await client.get(
            f"{base_url}/api/v1/packages/search",
            params={"q": "requests", "page": 1, "page_size": 10}
        )
        print(f"Search results: {response.json()['total']}")

        # 3. Get trends
        response = await client.get(
            f"{base_url}/api/v1/packages/requests/trends",
            params={"period": "7d"}
        )
        data = response.json()
        print(f"Trends for {data['name']}: {len(data['trends'])} data points")

asyncio.run(catalog_examples())
```

### Shell Commands

```bash
# List all packages
curl http://localhost:8000/api/v1/packages/

# Search packages
curl "http://localhost:8000/api/v1/packages/search?q=requests&page=1&page_size=10"

# Get trends
curl "http://localhost:8000/api/v1/packages/requests/trends?period=7d"

# Create package
curl -X POST http://localhost:8000/api/v1/packages/ \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-pkg", "summary": "Demo package", "license": "MIT"}'

# Update package
curl -X PUT http://localhost:8000/api/v1/packages/demo-pkg \
  -H "Content-Type: application/json" \
  -d '{"summary": "Updated summary"}'

# Delete package
curl -X DELETE http://localhost:8000/api/v1/packages/demo-pkg
```

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found |
| `422` | Invalid package name or missing `q` parameter |

---
*Catalog API documentation for PythonDepot*
