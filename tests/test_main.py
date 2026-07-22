"""Basic tests for PythonDepot API."""
from src.main import app

def test_root():
    assert app.title == "PythonDepot"
