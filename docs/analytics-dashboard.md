# Analytics Dashboard

The Analytics Dashboard provides package usage tracking, trending and popularity metrics, and event-based analytics for the PythonDepot platform.

## Endpoints

### Get Trending Packages

**GET** `/api/v1/analytics/trending`

Retrieves packages with the highest view growth.

**Response:**
```json
{
  "trending": [],
  "period": "7d"
}
```

When populated, each trending entry contains the package name.

### Get Popular Packages

**GET** `/api/v1/analytics/popular`

Retrieves the most popular packages by event count.

**Response:**
```json
{
  "popular": []
}
```

### Track Analytics Event

**POST** `/api/v1/analytics/events`

Records an analytics event (e.g., package view, install click, search).

**Request Body:**
```json
{
  "event_type": "package_view",
  "package_name": "requests",
  "user_id": "user123",
  "metadata": {"source": "search_results"}
}
```

**Response:**
```json
{
  "status": "tracked"
}
```

### Get Package Statistics

**GET** `/api/v1/analytics/stats/{package_name}`

Returns view and install counts for a package based on tracked events.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Response:**
```json
{
  "package": "requests",
  "views": 0,
  "installs": 0
}
```

---

## AnalyticsService

The `python_depot.pydepot.analytics.AnalyticsService` class provides the analytics logic:

| Method | Description |
|--------|-------------|
| `track_event(event_type, package_name, user_id, metadata_json)` | Persist an analytics event |
| `package_stats(package_name)` | Get view/install counts for a package |
| `trending_packages(period)` | Get trending packages by view count |
| `popular_packages()` | Get most popular packages by total events |
| `fetch_download_stats(package_name)` | Fetch download stats from PyPI Stats API (async) |

---

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def analytics_examples():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. Get trending
        response = await client.get(f"{base_url}/api/v1/analytics/trending")
        data = response.json()
        print(f"Trending period: {data['period']}")

        # 2. Get popular
        response = await client.get(f"{base_url}/api/v1/analytics/popular")
        data = response.json()
        print(f"Popular packages: {len(data['popular'])}")

        # 3. Track an event
        response = await client.post(
            f"{base_url}/api/v1/analytics/events",
            json={"event_type": "package_view", "package_name": "requests"}
        )
        print(f"Event tracked: {response.json()['status']}")

        # 4. Get package stats
        response = await client.get(f"{base_url}/api/v1/analytics/stats/requests")
        data = response.json()
        print(f"Package stats: {data['views']} views, {data['installs']} installs")

asyncio.run(analytics_examples())
```

### Shell Commands

```bash
# Get trending packages
curl http://localhost:8000/api/v1/analytics/trending

# Get popular packages
curl http://localhost:8000/api/v1/analytics/popular

# Track an event
curl -X POST http://localhost:8000/api/v1/analytics/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "package_view", "package_name": "requests"}'

# Get package stats
curl http://localhost:8000/api/v1/analytics/stats/requests
```

---

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `404` | Package not found in stats |
| `422` | Invalid event data |

---
*Analytics Dashboard documentation for PythonDepot*
