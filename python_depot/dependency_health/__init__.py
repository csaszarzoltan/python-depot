"""dependency_health — Vulnerability scanning, outdated checking, health scoring.

This module provides models and services for:
    - Vulnerability scanning via safety CLI and OSV.dev API
    - CVSS v3.1 health scoring and compatibility checks
    - Scan history tracking
    - Vulnerability alerting and webhook delivery
"""

from python_depot.dependency_health.alerts import AlertEngine
from python_depot.dependency_health.osv_client import OSVClient
from python_depot.dependency_health.scanner import DependencyScanner, HealthScanner
from python_depot.dependency_health.scoring import aggregate_score, calculate_severity

__all__ = [
    "AlertEngine",
    "HealthScanner",
    "DependencyScanner",
    "OSVClient",
    "aggregate_score",
    "calculate_severity",
]
