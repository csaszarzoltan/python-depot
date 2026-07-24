"""OSV.dev API client — vulnerability database queries.

Provides async HTTP client for OSV.dev REST API to query
vulnerabilities by package name/version and retrieve full
vulnerability details.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OSV_API_BASE = "https://api.osv.dev"
REQUEST_TIMEOUT = 30  # seconds


class OSVClient:
    """Async HTTP client for OSV.dev vulnerability database API.

    Handles single-package queries, batch queries, and vulnerability detail
    retrieval through the OSV.dev REST API.
    """

    def __init__(self, base_url: str = OSV_API_BASE) -> None:
        """Initialize the client with a base URL.

        Args:
            base_url: OSV.dev API base URL.
        """
        self.base_url = base_url.rstrip("/")

    async def query_package(
        self, name: str, version: str | None = None
    ) -> dict[str, Any]:
        """Query OSV.dev for vulnerabilities affecting a specific package version.

        Args:
            name: Package name (e.g. 'requests').
            version: Specific version string (e.g. '2.31.0'). When None,
                     queries all known vulnerabilities for the package.

        Returns:
            Dict with 'vulns' key containing list of vulnerability IDs
            and related metadata from OSV.dev.

        Raises:
            httpx.HTTPError: On network or API errors.
            httpx.TimeoutException: On request timeout.
        """
        payload: dict[str, Any] = {
            "package": {"name": name, "ecosystem": "PyPI"}
        }
        if version:
            payload["version"] = version

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            url = f"{self.base_url}/v1/query"
            logger.debug("Querying OSV.dev: %s -> %s", url, name)
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data

    async def query_batch(self, queries: list[dict]) -> list[dict]:
        """Batch query OSV.dev for multiple packages at once.

        Args:
            queries: List of query dicts, each with optional 'package'
                     (dict with 'name', 'ecosystem') and 'version' keys.

        Returns:
            List of response dicts, one per query, each containing
            vulnerability results for the requested package.

        Raises:
            httpx.HTTPError: On network or API errors.
        """
        if not queries:
            return []

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            url = f"{self.base_url}/v1/querybatch"
            logger.debug("Batch querying OSV.dev: %d queries", len(queries))
            resp = await client.post(url, json={"queries": queries})
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

    async def get_vuln_details(self, vuln_id: str) -> dict[str, Any]:
        """Fetch full vulnerability details from OSV.dev by vulnerability ID.

        Args:
            vuln_id: OSV vulnerability ID (e.g. 'GHSA-xxxx-xxxx-xxxx').

        Returns:
            Dict with full vulnerability details including CVSS vectors,
            affected ranges, references, and aliases.

        Raises:
            httpx.HTTPError: On network or API errors.
        """
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            url = f"{self.base_url}/v1/vulns/{vuln_id}"
            logger.debug("Fetching vuln details: %s", vuln_id)
            resp = await client.get(url)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data
