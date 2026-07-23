# Ratings API

The Ratings API provides comprehensive package rating and review functionality for the Python package catalog.

## Overview

The ratings system allows users to:
- Submit ratings for packages
- Retrieve rating information and summaries
- Access rating distributions
- Manage package feedback

## Endpoints

### Get Package Ratings

**GET** `/api/v1/ratings/{package_name}`

Retrieves all ratings for a specific package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "ratings": [
    {
      "id": 1,
      "user": "developer1",
      "score": 5,
      "review": "Excellent package!",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "average": 4.5,
  "total": 1
}
```

### Submit Rating

**POST** `/api/v1/ratings/{package_name}`

Submits a new rating for a package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Request Body:**
```json
{
  "user": "developer1",
  "score": 5,
  "review": "Excellent package! Very reliable and well-maintained.",
  "version": "2.31.0"
}
```

**Response:**
```json
{
  "package": "requests",
  "status": "rated",
  "rating": {
    "id": 1,
    "user": "developer1",
    "score": 5,
    "review": "Excellent package! Very reliable and well-maintained.",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Rating Summary

**GET** `/api/v1/ratings/{package_name}/summary`

Retrieves a summary of ratings including distribution statistics.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "summary": {
    "average": 4.5,
    "total": 1,
    "distribution": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 1,
      "5": 3
    },
    "breakdown": {
      "5": "Excellent",
      "4": "Good",
      "3": "Average",
      "2": "Below Average",
      "1": "Poor"
    }
  }
}
```

## Models

### Rating

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier |
| `package` | string | Package name |
| `user` | string | User who submitted rating |
| `score` | integer | Rating score (1-5) |
| `review` | string | Optional review text |
| `version` | string | Package version rated |
| `created_at` | datetime | Creation timestamp |

### Rating Summary

| Field | Type | Description |
|-------|------|-------------|
| `average` | float | Average rating score |
| `total` | integer | Total number of ratings |
| `distribution` | object | Count per score (1-5) |
| `breakdown` | object | Human-readable description per score |

## Example Usage

### Python Client

```python
import httpx
import asyncio
from typing import List

async def ratings_examples():
    base_url = "http://localhost:8000"
    
    # 1. Get existing ratings for a package
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v1/ratings/requests")
        ratings_data = response.json()
        print(f"Package: {ratings_data['package']}")
        print(f"Average rating: {ratings_data['average']}")
        print(f"Total ratings: {ratings_data['total']}")
        
        # 2. Submit a new rating
        new_rating = {
            "user": "new-developer",
            "score": 5,
            "review": "Perfect for API development!",
            "version": "2.31.0"
        }
        response = await client.post(
            f"{base_url}/api/v1/ratings/requests",
            json=new_rating
        )
        result = response.json()
        print(f"Submitted rating: {result['status']}")
        
        # 3. Get rating summary
        response = await client.get(f"{base_url}/api/v1/ratings/requests/summary")
        summary = response.json()
        print(f"Rating distribution: {summary['summary']['distribution']}")

# Run the examples
asyncio.run(ratings_examples())
```

### Shell Commands

```bash
# Get package ratings
curl http://localhost:8000/api/v1/ratings/requests

# Submit a rating
curl -X POST http://localhost:8000/api/v1/ratings/requests \
  -H "Content-Type: application/json" \
  -d '{
    "user": "demo-user",
    "score": 5,
    "review": "Great package for web development!",
    "version": "2.31.0"
  }'

# Get rating summary
curl http://localhost:8000/api/v1/ratings/requests/summary
```

## Testing

```bash
# Run rating-specific tests
pytest tests/test_ratings.py -v

# Test rating submission
pytest tests/test_ratings.py::test_get_ratings_returns_empty -v

# Test rating summary
pytest tests/test_ratings.py::test_rating_summary -v
```

## Error Handling

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found |
| `400` | Invalid request data |

### Example Error Response

```json
{
  "detail": "Package 'nonexistent-package' not found in catalog"
}
```

## Rate Limiting

Ratings endpoints have a rate limit of 100 requests per minute per IP address. Submissions are limited to 10 per minute.

## Integration with Catalog API

The Ratings API integrates with the Catalog API to provide a complete package feedback system:

1. **Package Discovery**: Users browse packages via Catalog API
2. **Rating Information**: Users see ratings via Ratings API
3. **Quality Signals**: Higher-rated packages get better visibility
4. **Continuous Feedback**: New ratings continuously update package scores

---
*Ratings API documentation for PythonDepot*