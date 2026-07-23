# Ratings & Reviews API

The Ratings & Reviews API provides package rating (1-5 stars) and review functionality with moderation support.

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
  "ratings": [],
  "average": 0.0
}
```

### Submit Rating

**POST** `/api/v1/ratings/{package_name}`

Submits or updates a rating for a package.

**Path Parameters:**
- `package_name` (string, required): The name of the package

**Request Body:**
```json
{
  "score": 5
}
```

**Response:**
```json
{
  "package": "requests",
  "status": "rated"
}
```

### Get Rating Summary

**GET** `/api/v1/ratings/{package_name}/summary`

Retrieves the rating distribution (count of each score 1-5).

**Response:**
```json
{
  "package": "requests",
  "distribution": {
    "1": 0,
    "2": 0,
    "3": 0,
    "4": 0,
    "5": 0
  }
}
```

### List Reviews

**GET** `/api/v1/reviews/{package_name}`

Lists all reviews for a package.

**Response:**
```json
{
  "package": "requests",
  "reviews": [],
  "total": 0
}
```

### Submit Review

**POST** `/api/v1/reviews/{package_name}`

Submits a new review. Pydantic-validated body with rating (1-5), comment, and reviewer fields.

**Request Body:**
```json
{
  "rating": 5,
  "comment": "Excellent HTTP library!",
  "reviewer": "demo-user"
}
```

**Response (201 Created):**
```json
{
  "package": "requests",
  "review_id": 1,
  "timestamp": "2026-07-23T13:00:00Z"
}
```

Validation rules:
- `rating`: integer, 1–5 (422 if out of range)
- `comment`: non-empty string
- `reviewer`: non-empty string

### Get Specific Review

**GET** `/api/v1/reviews/{package_name}/{review_id}`

Retrieves a specific review by ID.

**Response:**
```json
{
  "package": "requests",
  "review_id": 1,
  "found": false
}
```

## Example Usage

### Python Client

```python
import httpx
import asyncio

async def ratings_examples():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. Get ratings
        response = await client.get(f"{base_url}/api/v1/ratings/requests")
        data = response.json()
        print(f"Average rating: {data['average']}")

        # 2. Submit rating
        response = await client.post(
            f"{base_url}/api/v1/ratings/requests",
            json={"score": 5}
        )
        print(f"Rating status: {response.json()['status']}")

        # 3. Get rating summary
        response = await client.get(f"{base_url}/api/v1/ratings/requests/summary")
        data = response.json()
        print(f"Distribution: {data['distribution']}")

        # 4. Submit review
        response = await client.post(
            f"{base_url}/api/v1/reviews/requests",
            json={"rating": 5, "comment": "Great!", "reviewer": "demo"}
        )
        print(f"Review ID: {response.json()['review_id']}")

asyncio.run(ratings_examples())
```

### Shell Commands

```bash
# Get ratings
curl http://localhost:8000/api/v1/ratings/requests

# Submit rating
curl -X POST http://localhost:8000/api/v1/ratings/requests \
  -H "Content-Type: application/json" \
  -d '{"score": 5}'

# Get rating summary
curl http://localhost:8000/api/v1/ratings/requests/summary

# Submit review
curl -X POST http://localhost:8000/api/v1/reviews/requests \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Great package!", "reviewer": "demo-user"}'

# List reviews
curl http://localhost:8000/api/v1/reviews/requests
```

## Error Handling

| Status Code | Description |
|-------------|-------------|
| `200` | Request successful |
| `201` | Review created successfully |
| `404` | Package not found |
| `422` | Invalid rating (must be 1-5), empty comment or reviewer |

---
*Ratings & Reviews API documentation for PythonDepot*
