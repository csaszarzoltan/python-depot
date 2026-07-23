#!/usr/bin/env python3
"""
Reviews & Ratings Examples.

Demonstrates rating submission, review CRUD, and rating summary
retrieval using the PythonDepot API.

Prerequisites:
- PythonDepot server running locally (uvicorn python_depot.api:app --reload)
- httpx library installed
"""

import asyncio

import httpx


async def reviews_ratings_examples():
    """Example: Reviews and ratings operations."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🚀 Starting Reviews & Ratings Examples")
        print("=" * 50)

        # 1. Get existing ratings for a package
        print("\n1. ⭐ Getting ratings for 'requests'...")
        response = await client.get(f"{base_url}/api/v1/ratings/requests")
        ratings = response.json()
        print(f"   Package: {ratings['package']}")
        print(f"   Average rating: {ratings['average']}")
        print(f"   Total ratings: {len(ratings['ratings'])}")

        # 2. Submit a new rating
        print("\n2. ➕ Submitting a rating (score: 5)...")
        response = await client.post(
            f"{base_url}/api/v1/ratings/requests",
            json={"score": 5},
        )
        result = response.json()
        print(f"   Status: {result['status']}")

        # 3. Get rating summary with distribution
        print("\n3. 📊 Getting rating summary...")
        response = await client.get(
            f"{base_url}/api/v1/ratings/requests/summary"
        )
        summary = response.json()
        print(f"   Package: {summary['package']}")
        dist = summary["distribution"]
        for score in range(1, 6):
            print(f"   Score {score}: {dist.get(score, 0)} ratings")

        # 4. List reviews
        print("\n4. 💬 Listing reviews for 'requests'...")
        response = await client.get(f"{base_url}/api/v1/reviews/requests")
        reviews = response.json()
        print(f"   Package: {reviews['package']}")
        print(f"   Total reviews: {reviews['total']}")

        # 5. Submit a review
        print("\n5. ✍️ Submitting a review...")
        response = await client.post(
            f"{base_url}/api/v1/reviews/requests",
            json={
                "rating": 5,
                "comment": "Excellent HTTP library for Python!",
                "reviewer": "demo-user",
            },
        )
        review = response.json()
        print("   Status: 201 Created")
        print(f"   Review ID: {review['review_id']}")
        print(f"   Timestamp: {review['timestamp']}")

        # 6. Get the specific review
        print(f"\n6. 🔍 Getting review #{review['review_id']}...")
        response = await client.get(
            f"{base_url}/api/v1/reviews/requests/{review['review_id']}"
        )
        specific = response.json()
        print(f"   Package: {specific['package']}")
        print(f"   Found: {specific['found']}")

        print("\n✅ Reviews & ratings examples completed!")


if __name__ == "__main__":
    asyncio.run(reviews_ratings_examples())
