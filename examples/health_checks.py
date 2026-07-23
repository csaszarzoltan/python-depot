#!/usr/bin/env python3
"""
Health Checks & Vulnerability Scanning Examples.

Demonstrates system health check, vulnerability scanning, and
scan history retrieval using the PythonDepot API.

Prerequisites:
- PythonDepot server running locally (uvicorn python_depot.api:app --reload)
- httpx library installed
"""

import asyncio

import httpx


async def health_examples():
    """Example: Health checks and vulnerability scanning."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("🚀 Starting Health & Vulnerability Examples")
        print("=" * 50)

        # 1. Check system health
        print("\n1. ❤️ Checking system health...")
        response = await client.get(f"{base_url}/health")
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   Version: {health['version']}")
        print(f"   Uptime: {health['uptime']}")
        print(f"   Database: {health['db_status']}")
        print(f"   Timestamp: {health['timestamp']}")

        # 2. List vulnerability scans
        print("\n2. 🔒 Listing vulnerability scans for 'requests'...")
        response = await client.get(
            f"{base_url}/api/v1/vulnerabilities/requests"
        )
        scans = response.json()
        print(f"   Previous scans: {scans['total']}")

        # 3. Trigger a new vulnerability scan
        print("\n3. 🔍 Triggering new scan...")
        response = await client.post(
            f"{base_url}/api/v1/vulnerabilities/requests/scan"
        )
        scan_result = response.json()
        print(f"   Scan status: {scan_result['status']}")

        # 4. Get the latest scan result
        print("\n4. 📋 Getting latest scan result...")
        response = await client.get(
            f"{base_url}/api/v1/vulnerabilities/requests/latest"
        )
        latest = response.json()
        if latest.get("scan"):
            scan = latest["scan"]
            print(f"   Status: {scan['status']}")
            print(f"   Vulnerabilities: {scan['vulnerability_count']}")
            print(f"   Scanned at: {scan['scanned_at']}")
        else:
            print("   No scans available yet (safety CLI may not be installed)")

        print("\n✅ Health & vulnerability examples completed!")


if __name__ == "__main__":
    asyncio.run(health_examples())
