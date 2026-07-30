"""Small SQLite utilities shared by product modules."""
from __future__ import annotations
import sqlite3
from pathlib import Path

def connect(path: str | Path) -> sqlite3.Connection:
    db=sqlite3.connect(str(path),timeout=10)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db
