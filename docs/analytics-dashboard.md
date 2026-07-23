# Analytics Dashboard

The Analytics Dashboard provides comprehensive package usage, popularity, and trend analysis for the PythonDepot platform.

## Overview

The analytics system includes:
- Package usage statistics
- Trending and popularity metrics
- User behavior analytics
- Custom report generation
- Performance monitoring

## Features

### Package Analytics

- View counts and download statistics
- Installation trends over time
- Version popularity analysis
- Geographic distribution (if available)

### User Analytics

- User activity patterns
- Package interaction history
n- Search behavior analysis
- Engagement metrics

### System Analytics

- API performance metrics
- Database query performance
- System resource usage
- Error rate tracking

## Endpoints

### Get Trending Packages

**GET** `/api/v1/analytics/trending`

Retrieves packages with highest growth in views/downloads over the last 7 days.

**Response:**
```json
{
  "trending": [
    {
      "package": "mcp-sdk",
      "package_id": 1,
      "growth_rate": 125.5,
      "views_7d": 1250,
      "downloads_7d": 450,
      "rank": 1,
      "category": "developer-tools"
    },
    {
      "package": "fastapi-utils",
      "package_id": 2,
      "growth_rate": 89.2,
      "views_7d": 892,
      "downloads_7d": 320,
      "rank": 2,
      "category": "web-frameworks"
    }
  ],
  "period": "7d",
  "total_packages": 50
}
```

### Get Popular Packages

**GET** `/api/v1/analytics/popular`

Retrieves the most popular packages based on total downloads/views.

**Response:**
```json
{
  "popular": [
    {
      "package": "requests",
      "package_id": 1,
      "total_downloads": 1500000,
      "total_views": 5000000,
      "rank": 1,
      "category": "http-client",
      "rating": 4.5
    },
    {
      "package": "django",
      "package_id": 2,
      "total_downloads": 800000,
      "total_views": 3500000,
      "rank": 2,
      "category": "web-framework",
      "rating": 4.2
    }
  ],
  "period": "all-time"
}
```

### Track Analytics Event

**POST** `/api/v1/analytics/events`

Records an analytics event for tracking user behavior.

**Request Body:**
```json
{
  "event_type": "package_view",
  "package_name": "requests",
  "user_id": "user123",
  "session_id": "sess_abc123",
  "source": "search_results",
  "metadata": {
    "referrer": "https://example.com",
    "page_load_time": 1250,
    "device_type": "desktop"
  }
}
```

**Response:**
```json
{
  "status": "tracked",
  "event_id": "event_20240115_001",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Get Package Statistics

**GET** `/api/v1/analytics/stats/{package_name}`

Retrieves detailed statistics for a specific package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "stats": {
    "total_views": 5000000,
    "total_downloads": 1500000,
    "views_7d": 45000,
    "downloads_7d": 12000,
    "views_30d": 200000,
    "downloads_30d": 65000,
    "average_rating": 4.5,
    "rating_count": 1250,
    "version_distribution": {
      "2.31.0": 800000,
      "2.30.0": 500000,
      "2.29.0": 200000
    },
    "age_in_days": 1800,
    "first_release": "2010-01-01",
    "last_update": "2024-01-10"
  }
}
```

## Models

### Trending Package

| Field | Type | Description |
|-------|------|-------------|
| `package` | string | Package name |
| `package_id` | integer | Unique package identifier |
| `growth_rate` | float | Percentage growth over period |
| `views_7d` | integer | Views in last 7 days |
| `downloads_7d` | integer | Downloads in last 7 days |
| `rank` | integer | Current ranking |
| `category` | string | Package category |

### Popular Package

| Field | Type | Description |
|-------|------|-------------|
| `package` | string | Package name |
| `package_id` | integer | Unique package identifier |
| `total_downloads` | integer | Total downloads (all-time) |
| `total_views` | integer | Total views (all-time) |
| `rank` | integer | Current ranking |
| `category` | string | Package category |
| `rating` | float | Average rating |

### Analytics Event

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Type of event (package_view, download, rating, etc.) |
| `package_name` | string | Package associated with event |
| `user_id` | string | User ID (optional) |
| `session_id` | string | Session identifier |
| `source` | string | Source of the event |
| `metadata` | object | Additional event metadata |

## Example Usage

### Python Client

```python
import httpx
import asyncio
import json
from typing import List, Dict

async def analytics_examples():
    base_url = "http://localhost:8000"
    
    # 1. Get trending packages
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v1/analytics/trending")
        trending = response.json()
        print(f"Trending packages for {trending['period']}:")
        for i, package in enumerate(trending['trending'], 1):
            print(f"  {i}. {package['package']} - Growth: {package['growth_rate']:.1f}%")
        
        # 2. Get popular packages
        response = await client.get(f"{base_url}/api/v1/analytics/popular")
        popular = response.json()
        print(f"\nMost popular packages ({popular['period']}):")
        for package in popular['popular'][:5]:
            print(f"  • {package['package']} - Downloads: {package['total_downloads']:,}")
            
        # 3. Track an analytics event
        event = {
            "event_type": "package_view",
            "package_name": "requests",
            "user_id": "demo-user-123",
            "session_id": "sess_demo_456",
            "source": "tutorial",
            "metadata": {
                "referrer": "https://python.org",
                "page_load_time": 1500,
                "device_type": "desktop"
            }
        }
        response = await client.post(f"{base_url}/api/v1/analytics/events", json=event)
        result = response.json()
        print(f"\nTracked event: {result['status']}")
        
        # 4. Get package statistics
        response = await client.get(f"{base_url}/api/v1/analytics/stats/requests")
        stats = response.json()
        print(f"\nPackage: {stats['package']}")
        print(f"  Views: {stats['stats']['total_views']:,}")
        print(f"  Downloads: {stats['stats']['total_downloads']:,}")
        print(f"  Rating: {stats['stats']['average_rating']:.1f}/5.0")

# Run the examples
asyncio.run(analytics_examples())
```

### Shell Commands

```bash
# Get trending packages
curl http://localhost:8000/api/v1/analytics/trending

# Get popular packages
curl http://localhost:8000/api/v1/analytics/popular

# Track an analytics event
curl -X POST http://localhost:8000/api/v1/analytics/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "package_view",
    "package_name": "requests",
    "user_id": "demo-user",
    "session_id": "sess_demo",
    "source": "manual",
    "metadata": {
      "referrer": "https://example.com",
      "page_load_time": 1000,
      "device_type": "desktop"
    }
  }'

# Get package statistics
curl http://localhost:8000/api/v1/analytics/stats/requests
```

## Testing

```bash
# Run analytics-specific tests
pytest tests/test_analytics.py -v

# Test trending packages
pytest tests/test_analytics.py::test_trending_packages -v

# Test popular packages
pytest tests/test_analytics.py::test_popular_packages -v

# Test package stats
pytest tests/test_analytics.py::test_package_stats -v
```

## Error Handling

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found |
| `400` | Invalid event data |
| `422` | Validation error in event data |

### Example Error Response

```json
{
  "detail": "Package 'nonexistent-package' not found in catalog"
}
```

## Report Generation

The analytics dashboard supports various report formats:

### Usage Reports
```bash
# Generate daily usage report
python scripts/generate_report.py --type daily --output reports/daily_$(date +%Y%m%d).json

# Generate monthly analytics report
python scripts/generate_report.py --type monthly --output reports/monthly_$(date +%Y%m).json
```

### Example Report Structure

```json
{
  "report_type": "daily",
  "date": "2024-01-15",
  "metrics": {
    "total_views": 45000,
    "total_downloads": 12000,
    "new_packages": 5,
    "active_users": 1500,
    "top_packages": ["requests", "django", "flask"]
  },
  "trending": [
    {
      "package": "mcp-sdk",
      "growth": 125.5
    }
  ]
}
```

## Integration with Other APIs

The Analytics API integrates with:

1. **Catalog API**: Provides package metadata
2. **Ratings API**: Retrieves rating data for analytics
3. **Health API**: Includes security metrics in reports
4. **Monitoring**: Performance metrics feed into analytics

## Rate Limiting

Analytics endpoints have the following rate limits:

| Endpoint | Rate Limit | Burst Limit |
|----------|------------|-------------|
| `/trending` | 100/min | 20 |
| `/popular` | 100/min | 20 |
| `/events` | 1000/min | 100 |
| `/stats/{package}` | 200/min | 50 |

## Performance Considerations

1. **Caching**: Analytics data should be cached for 5-15 minutes
2. **Database Indexes**: Ensure proper indexes on analytics tables
3. ** Asynchronous Processing**: Event tracking should use async processing
4. ** Data Retention**: Archive older analytics data periodically

## Configuration

### Analytics Settings

```python
# config/analytics.py
ANALYTICS_CONFIG = {
    "cache_timeout": 300,  # 5 minutes
    "max_trending_days": 30,
    "event_batch_size": 100,
    "retention_days": 365,
    "trending_threshold": 50,  # minimum views to appear in trending
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANALYTICS_DB_URL` | Database connection string | `sqlite:///analytics.db` |
| `ANALYTICS_CACHE_URL` | Cache backend URL | Redis URL |
| `ANALYTICS_BATCH_SIZE` | Batch size for event processing | 100 |
| `ANALYTICS_REPORT_DIR` | Directory for report outputs | `./reports` |

---
*Analytics Dashboard documentation for PythonDepot*