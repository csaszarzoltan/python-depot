#!/usr/bin/env python3
"""
Dependency Scanning & Security Dashboard Examples.

Demonstrates:
  1. CVSS v3.1 scoring engine (no server required)
  2. OSV.dev client usage
  3. Security Dashboard API endpoints
  4. Alert engine (detection + webhook)

Prerequisites:
  - PythonDepot server running locally (uvicorn python_depot.api:app --reload)
  - httpx library installed
"""

import asyncio

import httpx


# ---------------------------------------------------------------------------
# Part 1 — CVSS v3.1 Scoring Engine (pure Python, no server required)
# ---------------------------------------------------------------------------

def scoring_examples():
    """CVSS v3.1 scoring examples using the local scoring module."""
    print("=" * 60)
    print("1. CVSS v3.1 Scoring Engine")
    print("=" * 60)

    from python_depot.dependency_health.scoring import (
        aggregate_score,
        calculate_severity,
    )

    # 1a. Parse a CVSS v3.1 vector
    print("\n1a. calculate_severity — parse a vector string")
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    result = calculate_severity(vector)
    print(f"    Vector: {result['vector']}")
    print(f"    Score:  {result['score']}")
    print(f"    Severity: {result['severity']}")
    # → Score: 9.8, Severity: CRITICAL

    # 1b. Known severity thresholds
    print("\n1b. Severity thresholds:")
    examples = [
        ("NONE",    "CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:N/I:N/A:N"),
        ("LOW",     "CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N"),
        ("MEDIUM",  "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N"),
        ("HIGH",    "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N"),
        ("CRITICAL","CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
    ]
    for label, vec in examples:
        r = calculate_severity(vec)
        print(f"    {label:10s} → score={r['score']:5.1f}  vector={vec[:50]}...")

    # 1c. Aggregate multiple vulnerabilities
    print("\n1c. aggregate_score — combine multiple vulns into health score")
    vulns = [
        {"severity": "CRITICAL", "score": 9.8, "fixed": False},
        {"severity": "HIGH",     "score": 7.5, "fixed": False},
        {"severity": "MEDIUM",   "score": 5.3, "fixed": False},
        {"severity": "LOW",      "score": 2.1, "fixed": True},
    ]
    agg = aggregate_score(vulns)
    print(f"    Total:         {agg['total']}")
    print(f"    Max severity:  {agg['max_severity']}")
    print(f"    Vuln count:    {agg['vuln_count']}")
    print(f"    Avg score:     {agg['avg_score']}")
    print(f"    Breakdown:     {agg['breakdown']}")

    # 1d. Error handling
    print("\n1d. Error handling — invalid vector")
    try:
        calculate_severity("invalid-vector")
    except ValueError as e:
        print(f"    ValueError: {e}")


# ---------------------------------------------------------------------------
# Part 2 — OSV.dev Client (needs network, async)
# ---------------------------------------------------------------------------

async def osv_examples():
    """OSV.dev API client examples."""
    print("\n" + "=" * 60)
    print("2. OSV.dev Client")
    print("=" * 60)

    from python_depot.dependency_health.osv_client import OSVClient

    client = OSVClient()

    # 2a. Query a specific package version
    print("\n2a. query_package — scan requests 2.31.0")
    try:
        result = await client.query_package("requests", "2.31.0")
        vulns = result.get("vulns", [])
        print(f"    Vulnerabilities found: {len(vulns)}")
        if vulns:
            for v in vulns[:3]:
                print(f"      - {v.get('id', '?')}: {v.get('aliases', [])}")
    except Exception as e:
        print(f"    Error: {e} (OSV.dev may be unreachable)")

    # 2b. Batch query
    print("\n2b. query_batch — multiple packages at once")
    try:
        queries = [
            {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.31.0"},
            {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "2.3.0"},
        ]
        results = await client.query_batch(queries)
        print(f"    Batch results: {len(results)}")
        for i, r in enumerate(results):
            vulns = r.get("vulns", [])
            print(f"      Query {i+1}: {len(vulns)} vulns")
    except Exception as e:
        print(f"    Error: {e}")

    # 2c. Get vulnerability details
    print("\n2c. get_vuln_details — fetch details by vuln ID")
    try:
        details = await client.get_vuln_details("GHSA-xxxx-xxxx-xxxx")
        print(f"    Retrieved details for: {details.get('id', 'N/A')}")
    except Exception as e:
        print(f"    Error: {e}")


# ---------------------------------------------------------------------------
# Part 3 — Security Dashboard API (needs running server)
# ---------------------------------------------------------------------------

async def dashboard_examples():
    """Security dashboard API examples."""
    print("\n" + "=" * 60)
    print("3. Security Dashboard API")
    print("=" * 60)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 3a. Overview
        print("\n3a. GET /api/v1/dependency-health/overview")
        try:
            resp = await client.get(f"{base_url}/api/v1/dependency-health/overview")
            data = resp.json()
            print(f"    Total packages: {data['total_packages']}")
            print(f"    Total scans:    {data['total_scans']}")
            print(f"    Coverage:       {data['scan_coverage']}%")
        except Exception as e:
            print(f"    Error: {e}")

        # 3b. Trends
        print("\n3b. GET /api/v1/dependency-health/trends")
        try:
            resp = await client.get(f"{base_url}/api/v1/dependency-health/trends")
            data = resp.json()
            print(f"    Trend data points: {len(data['trends'])}")
        except Exception as e:
            print(f"    Error: {e}")

        # 3c. Packages sorted by vuln count
        print("\n3c. GET /api/v1/dependency-health/packages")
        try:
            resp = await client.get(
                f"{base_url}/api/v1/dependency-health/packages",
                params={"sort_by": "vuln_count", "limit": 5},
            )
            data = resp.json()
            print(f"    Total packages tracked: {data['total']}")
            for pkg in data["packages"]:
                print(f"      ID {pkg['package_id']}: {pkg['vuln_count']} vulns, status={pkg['status']}")
        except Exception as e:
            print(f"    Error: {e}")

        # 3d. Alerts
        print("\n3d. GET /api/v1/dependency-health/alerts")
        try:
            resp = await client.get(
                f"{base_url}/api/v1/dependency-health/alerts",
                params={"severity": "HIGH"},
            )
            data = resp.json()
            print(f"    Total alerts (HIGH+): {data['total']}")
            for alert in data["alerts"][:5]:
                print(f"      {alert['vuln_id']}: {alert['severity']} (score={alert['score']})")
        except Exception as e:
            print(f"    Error: {e}")

        # 3e. Package score
        print("\n3e. GET /api/v1/dependency-health/requests/score")
        try:
            resp = await client.get(f"{base_url}/api/v1/dependency-health/requests/score")
            data = resp.json()
            print(f"    Package:      {data['package']}")
            print(f"    Score:        {data['score']}/100")
            print(f"    Label:        {data['score_label']}")
            print(f"    Vuln count:   {data['vuln_count']}")
            print(f"    Max severity: {data['max_severity']}")
        except Exception as e:
            print(f"    Error: {e}")


# ---------------------------------------------------------------------------
# Part 4 — Alert Engine (library usage, no server required)
# ---------------------------------------------------------------------------

def alert_examples():
    """Alert engine usage examples."""
    print("\n" + "=" * 60)
    print("4. Alert Engine (library usage)")
    print("=" * 60)

    from python_depot.dependency_health.alerts import AlertEngine

    # 4a. Initialise with severity threshold
    print("\n4a. Constructor configuration")
    engine = AlertEngine(
        db=None,  # type: ignore  # no DB — will still detect new vulns
        webhook_url="https://hooks.example.com/alerts",
        severity_threshold="HIGH",
    )
    print(f"    Webhook URL:      {engine.webhook_url}")
    print(f"    Severity threshold: {engine.severity_threshold}")

    # 4b. Check new vulns from a scan (without DB — returns all as new)
    print("\n4b. check_new_vulns — detect new vulnerabilities")
    current_scan = {
        "package": "requests",
        "vulns": [
            {"id": "GHSA-xxxx-xxxx-xxxx", "severity": "CRITICAL", "score": 9.8},
            {"id": "GHSA-yyyy-yyyy-yyyy", "severity": "HIGH", "score": 7.5},
        ],
    }
    new_vulns = engine.check_new_vulns("requests", current_scan)
    print(f"    New vulnerabilities detected: {len(new_vulns)}")
    for v in new_vulns:
        print(f"      - {v['vuln_id']}: {v['severity']} (score={v.get('score', 'N/A')})")

    # 4c. Fire webhook
    print("\n4c. fire_webhook — attempt delivery")
    import asyncio
    result = asyncio.run(engine.fire_webhook(new_vulns[0]))
    print(f"    Webhook delivery: {'sent' if result else 'skipped/failed'}")

    # 4d. List alerts (empty without DB)
    print("\n4d. list_alerts — alert history")
    alerts = engine.list_alerts(severity="HIGH")
    print(f"    Alert count: {len(alerts)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("🔒 PythonDepot Security Scanning Examples")
    print()

    # Part 1: Scoring (pure Python)
    scoring_examples()

    # Part 2: OSV.dev client (network)
    await osv_examples()

    # Part 3: Dashboard API (server needed)
    await dashboard_examples()

    # Part 4: Alert engine (library)
    alert_examples()

    print("\n" + "=" * 60)
    print("✅ Dependency scanning examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
