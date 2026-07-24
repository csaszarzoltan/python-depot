#!/usr/bin/env python3
"""Dependency scanning and security dashboard examples for PythonDepot.

Demonstrates:
- OSV.dev vulnerability scanning
- Security dashboard: overview, trends, alerts
- Package health scoring
- Alert webhook simulation

Requires a running PythonDepot server at http://localhost:8000.
"""

import asyncio

import httpx

BASE_URL = "http://localhost:8000"


async def list_vulnerability_scans(client: httpx.AsyncClient) -> None:
    """List all vulnerability scans for a package."""
    print("\n=== 1. List Vulnerability Scans ===")
    response = await client.get(f"{BASE_URL}/api/v1/vulnerabilities/requests")
    data = response.json()
    print(f"  Package: {data['package']}")
    print(f"  Total scans: {data['total']}")
    for scan in data.get("scans", []):
        print(f"    Scan #{scan['id']}: {scan['status']} "
              f"({scan['vulnerability_count']} vulns, {scan['scanned_at']})")


async def trigger_scan(client: httpx.AsyncClient) -> None:
    """Trigger a new vulnerability scan."""
    print("\n=== 2. Trigger Vulnerability Scan ===")
    response = await client.post(f"{BASE_URL}/api/v1/vulnerabilities/requests/scan")
    data = response.json()
    print(f"  Package: {data['package']}")
    print(f"  Status: {data['status']}")
    print(f"  Scan ID: {data.get('scan_id', 'N/A')}")


async def get_latest_scan(client: httpx.AsyncClient) -> None:
    """Get the most recent scan result."""
    print("\n=== 3. Get Latest Scan ===")
    response = await client.get(f"{BASE_URL}/api/v1/vulnerabilities/requests/latest")
    data = response.json()
    scan = data.get("scan")
    if scan:
        print(f"  Scan #{scan['id']}: {scan['status']} "
              f"({scan['vulnerability_count']} vulns, {scan['scanned_at']})")
    else:
        print("  No scans yet")


async def dashboard_overview(client: httpx.AsyncClient) -> None:
    """Get aggregate vulnerability statistics."""
    print("\n=== 4. Security Dashboard Overview ===")
    response = await client.get(f"{BASE_URL}/api/v1/dependency-health/overview")
    data = response.json()
    print(f"  Total packages: {data['total_packages']}")
    print(f"  Total scans: {data['total_scans']}")
    print(f"  Coverage: {data['scan_coverage']}%")
    print(f"  Status: {data['vuln_counts']['vulnerable']} vulnerable, "
          f"{data['vuln_counts']['clean']} clean, "
          f"{data['vuln_counts']['unknown']} unknown")
    if data.get("last_scan"):
        print(f"  Last scan: {data['last_scan']}")


async def vulnerability_trends(client: httpx.AsyncClient) -> None:
    """Get vulnerability trend data over time."""
    print("\n=== 5. Vulnerability Trends ===")
    response = await client.get(f"{BASE_URL}/api/v1/dependency-health/trends")
    data = response.json()
    trends = data.get("trends", [])
    print(f"  Data points: {len(trends)}")
    for t in trends[-3:]:  # Show last 3 entries
        print(f"    {t['timestamp']}: {t['vulnerable']} vulnerable, "
              f"{t['clean']} clean, {t['total']} total")


async def package_health_score(client: httpx.AsyncClient) -> None:
    """Get composite security score for a package."""
    print("\n=== 6. Package Health Score ===")
    response = await client.get(f"{BASE_URL}/api/v1/dependency-health/requests/score")
    data = response.json()
    print(f"  Package: {data['package']}")
    print(f"  Score: {data['score']} ({data['score_label']})")
    print(f"  Vulns: {data['vuln_count']}")
    print(f"  Max severity: {data['max_severity']}")
    print(f"  Breakdown: {data['breakdown']}")


async def list_alerts(client: httpx.AsyncClient) -> None:
    """List recent vulnerability alerts."""
    print("\n=== 7. Recent Alerts ===")
    response = await client.get(f"{BASE_URL}/api/v1/dependency-health/alerts")
    data = response.json()
    print(f"  Total alerts: {data['total']}")
    for alert in data.get("alerts", []):
        print(f"    Alert #{alert['id']}: {alert['vuln_id']} "
              f"({alert['severity']}, score={alert['score']}, "
              f"webhook={alert['webhook_status']})")


async def list_packages_by_health(client: httpx.AsyncClient) -> None:
    """List packages sorted by health score."""
    print("\n=== 8. Packages by Health Score ===")
    response = await client.get(
        f"{BASE_URL}/api/v1/dependency-health/packages",
        params={"sort_by": "vuln_count", "limit": 5},
    )
    data = response.json()
    print(f"  Total packages tracked: {data['total']}")
    for pkg in data.get("packages", []):
        print(f"    Package #{pkg['package_id']}: {pkg['vuln_count']} vulns, "
              f"{pkg['status']} (last: {pkg['last_scan']})")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        # Check server is up
        try:
            health = await client.get(f"{BASE_URL}/health")
            health.raise_for_status()
            print(f"✓ Connected to PythonDepot at {BASE_URL}")
            print(f"  Status: {health.json()['status']}")
        except httpx.HTTPError as exc:
            print(f"✗ Cannot connect to {BASE_URL}: {exc}")
            print("  Start the server with: uvicorn python_depot.api:app --reload")
            return

        await list_vulnerability_scans(client)
        await trigger_scan(client)
        await get_latest_scan(client)
        await dashboard_overview(client)
        await vulnerability_trends(client)
        await package_health_score(client)
        await list_alerts(client)
        await list_packages_by_health(client)

    print("\n✓ All security scanning examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
