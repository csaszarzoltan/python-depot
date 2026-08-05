"""python_depot — Core modules for PythonDepot.

Sub-packages:
    dependency_health — Vulnerability scanning, outdated checking, health scoring.
    ecosystem         — Package manager detection, scanning, stats, migration guides.
    pydepot           — PyPI stats, GitHub metadata, trend analysis, forecasts.
    ratings           — Community ratings & reviews system.
"""

# Single source of truth for the API version — keep in sync with pyproject.toml.
# api.py and tests import this so the version can never drift again
# (previously hardcoded in 3 places: api.py said 0.5.0, tests asserted 0.1.0).
__version__ = "0.11.0"
