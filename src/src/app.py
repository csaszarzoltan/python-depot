"""FastAPI application factory for PythonDepot.

Re-exports from python_depot.api for backward compatibility with existing
imports (from src.app import app, create_app).
"""
# Re-export from the canonical api module so existing tests and imports
# (from src.app import app, create_app) work unchanged.
from python_depot.api import app, create_app  # noqa: F401
