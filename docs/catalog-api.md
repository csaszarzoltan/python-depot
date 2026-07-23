# Catalog API

The Catalog API provides comprehensive package discovery and management functionality for Python packages.

## Overview

The catalog system allows you to:
- Browse all available packages
- Search for specific packages by name
- Create, update, and delete package entries
- Access detailed package metadata

## Endpoints

### List All Packages

**GET** `/api/v1/packages/`

Returns a list of all packages in the catalog.

**Response:**
```json
{
  "packages": [
    {
      "id": 1,
      "name": "requests",
      "summary": "HTTP library",
      "description": "Requests is a port of cURL for Python",
      "homepage": "https://requests.readthedocs.io",
      "repository": "https://github.com/psf/requests",
      "author": "Kenneth Reitz",
      "license": "Apache-2.0",
      "latest_version": "2.31.0"
    }
  ],
  "total": 1
}
```

### Get Package Details

**GET** `/api/v1/packages/{package_name}`

Retrieves detailed information about a specific package.

**Path Parameters:**
- `package_name` (string, required): The name of the package to retrieve

**Response:**
```json
{
  "name": "requests",
  "found": true,
  "summary": "HTTP library",
  "description": "Requests is a port of cURL for Python",
  "homepage": "https://requests.readthedocs.io",
  "repository": "https://github.com/psf/requests",
  "author": "Kenneth Reitz",
  "license": "Apache-2.0",
  "latest_version": "2.31.0"
}
```

### Create New Package

**POST** `/api/v1/packages/`

Creates a new package entry in the catalog.

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
  "status": "created",
  "package": {
    "name": "new-package",
    "id": 2
  }
}
```

### Update Package

**PUT** `/api/v1/packages/{package_name}`

Updates an existing package's metadata.

**Path Parameters:**
- `package_name` (string, required): The name of the package to update

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

**Path Parameters:**
- `package_name` (string, required): The name of the package to delete

**Response:**
```json
{
  "name": "new-package",
  "status": "deleted"
}
```

## Models

### Package

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier |
| `name` | string | Package name (unique) |
| `summary` | string | Brief package summary |
| `description` | string | Detailed description |
| `homepage` | string | Official homepage URL |
| `repository` | string | Source repository URL |
| `author` | string | Package author |
| `license` | string | License type |
| `latest_version` | string | Latest available version |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def catalog_examples():
    base_url = "http://localhost:8000"
    
    # 1. List all packages
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v1/packages/")
        packages = response.json()
        print(f"Found {packages['total']} packages")
        
        # 2. Get specific package
        response = await client.get(f"{base_url}/api/v1/packages/requests")
        package = response.json()
        print(f"Package found: {package['found']}")
        
        # 3. Create new package
        new_package = {
            "name": "mcp-sdk",
            "summary": "Model Context Protocol SDK for Python",
            "description": "A Python SDK for building MCP servers and clients",
            "homepage": "https://github.com/modelcontextprotocol/sdk-python",
            "repository": "https://github.com/modelcontextprotocol/sdk-python",
            "author": "Model Context Protocol Team",
            "license": "MIT",
            "latest_version": "0.1.0"
        }
        response = await client.post(f"{base_url}/api/v1/packages/", json=new_package)
        result = response.json()
        print(f"Created package: {result}")

# Run the examples
asyncio.run(catalog_examples())
```

### Shell Commands

```bash
# List all packages
curl http://localhost:8000/api/v1/packages/

# Get package details
curl http://localhost:8000/api/v1/packages/requests

# Create new package
curl -X POST http://localhost:8000/api/v1/packages/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-sdk",
    "summary": "Model Context Protocol SDK for Python",
    "description": "A Python SDK for building MCP servers and clients",
    "homepage": "https://github.com/modelcontextprotocol/sdk-python",
    "repository": "https://github.com/modelcontextprotocol/sdk-python",
    "author": "Model Context Protocol Team",
    "license": "MIT",
    "latest_version": "0.1.0"
  }'
```

## Testing

```bash
# Run catalog-specific tests
pytest tests/test_packages.py -v

# Test with specific package
pytest tests/test_packages.py::test_get_package_not_found -v
```

## Rate Limiting

Catalog endpoints do not currently enforce rate limiting. For production use, consider implementing rate limiting middleware.

---
*Catalog API documentation for PythonDepot*