"""Database configuration and session management for python_depot modules.

Provides a shared Base for SQLAlchemy models and a session factory.
Import Base from here to define models inside the python_depot sub-packages.
"""
import os

import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Overridable so test runs can isolate per-process (see tests/conftest.py).
# Parallel kanban workers sharing /tmp/python_depot.db caused drop/create
# races ("table already exists" / "no such table") in the test suite.
DATABASE_URL = os.environ.get("PYTHON_DEPOT_DATABASE_URL", "sqlite:////tmp/python_depot.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database models."""


def get_db():
    """Yield a database session for use in dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Drop all tables and recreate them — use in tests for isolation.

    Handles fresh databases gracefully by catching ``OperationalError``
    during drop when tables don't exist yet.
    """
    try:
        Base.metadata.drop_all(bind=engine)
    except sqlalchemy.exc.OperationalError:
        # Fresh DB — tables may not exist yet; ignore drop failures
        pass
    Base.metadata.create_all(bind=engine)
