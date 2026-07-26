"""Ecosystem & Migration Hub — package manager detection, scanning, stats, migration guides.

Sub-modules:
    detector — PackageManagerDetector (PyPI JSON + pyproject.toml analysis)
    scanner  — EcosystemScanner (per-package and batch scanning)
    stats    — EcosystemStatsService (aggregation, adoption rates, compatibility matrix)
    migration — MigrationGuideGenerator (templated markdown guides)
    models   — SQLAlchemy DB models (PackageScan, EcosystemStatsSnapshot)
"""
