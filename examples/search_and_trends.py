#!/usr/bin/env python3
"""
Search & Trends Examples.

Demonstrates package search with pagination and time-series
trend data retrieval using the PythonDepot API.

Prerequisites:
- PythonDepot server running locally (uvicorn python_depot.api:app --reload)
- httpx library installed
"""

import asyncio

import httpx


async def search_trends_examples():
    """Example: Package search and trends."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🚀 Starting Search & Trends Examples")
        print("=" * 50)

        # 1. Search packages with default pagination
        print("\n1. 🔍 Searching for 'requests' (page 1, page_size 10)...")
        response = await client.get(
            f"{base_url}/api/v1/packages/search",
            params={"q": "requests", "page": 1, "page_size": 10},
        )
        search_data = response.json()
        print(f"   Query: {search_data['query']}")
        print(f"   Results: {search_data['total']}")
        for result in search_data["results"]:
            print(f"   - {result['name']} (score: {result['score']})")

        # 2. Search with a broader query
        print("\n2. 🌐 Searching for 'fastapi'...")
        response = await client.get(
            f"{base_url}/api/v1/packages/search",
            params={"q": "fastapi", "page": 1, "page_size": 5},
        )
        search_data = response.json()
        print(f"   Total results: {search_data['total']}")
        for result in search_data["results"]:
            print(f"   - {result['name']}")

        # 3. Get 7-day trends
        print("\n3. 📈 Getting 7-day trends for 'requests'...")
        response = await client.get(
            f"{base_url}/api/v1/packages/requests/trends",
            params={"period": "7d"},
        )
        trends = response.json()
        print(f"   Package: {trends['name']}")
        print(f"   Period: {trends['period']}")
        print(f"   Data points: {len(trends['trends'])}")
        for day in trends["trends"][:3]:
            print(
                f"   - {day['date']}: "
                f"{day['downloads']} downloads, {day['stars']} stars"
            )

        # 4. Get 30-day trends
        print("\n4. 📊 Getting 30-day trends...")
        response = await client.get(
            f"{base_url}/api/v1/packages/requests/trends",
            params={"period": "30d"},
        )
        trends = response.json()
        print(f"   Data points: {len(trends['trends'])}")
        print(f"   First: {trends['trends'][0]}")
        print(f"   Last: {trends['trends'][-1]}")

        print("\n✅ Search & trends examples completed!")


if __name__ == "__main__":
    asyncio.run(search_trends_examples())
