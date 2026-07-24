"""Tests for VulnerabilityAlert model — schema, CRUD, indexes.

Pattern:
- Interface tests: verify the model exists, has correct columns, types,
  constraints — these PASS immediately.
- Behavioral tests: verify CRUD operations, querying, index behaviour —
  these raise NotImplementedError until the model is fully wired.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from python_depot.database import SessionLocal, reset_db
from python_depot.dependency_health.models import VulnerabilityAlert

# ---------------------------------------------------------------------------
# Interface tests — pass immediately (import, model class, table columns)
# ---------------------------------------------------------------------------


class TestInterfaceAlertModel:
    """Verify VulnerabilityAlert model contract."""

    def test_model_imports(self):
        """VulnerabilityAlert can be imported without error."""
        assert VulnerabilityAlert is not None
        assert VulnerabilityAlert.__tablename__ == "vulnerability_alerts"

    def test_model_is_sqlalchemy_model(self):
        """VulnerabilityAlert is a proper SQLAlchemy model with a table."""
        assert hasattr(VulnerabilityAlert, "__table__")
        assert VulnerabilityAlert.__table__.name == "vulnerability_alerts"

    def test_table_columns(self):
        """vulnerability_alerts table has all expected columns."""
        cols = {c.name for c in VulnerabilityAlert.__table__.columns}
        expected = {
            "id",
            "package_id",
            "vuln_id",
            "severity",
            "score",
            "details",
            "webhook_status",
            "created_at",
        }
        missing = expected - cols
        extra = cols - expected
        assert not missing, f"Missing columns: {missing}"
        assert not extra, f"Unexpected columns: {extra}"

    def test_column_types(self):
        """Each column has the expected SQLAlchemy type (inspected via ORM)."""
        mapper = inspect(VulnerabilityAlert)
        col_map = {c.name: c.type for c in mapper.columns}

        from sqlalchemy import DateTime, Float, Integer, String, Text

        assert isinstance(col_map["id"], Integer)
        assert isinstance(col_map["package_id"], Integer)
        assert isinstance(col_map["vuln_id"], String)
        assert isinstance(col_map["severity"], String)
        assert isinstance(col_map["score"], (Float, type(None)))
        assert isinstance(col_map["details"], (Text, type(None)))
        assert isinstance(col_map["webhook_status"], String)
        assert isinstance(col_map["created_at"], DateTime)

    def test_package_id_nullable_false(self):
        """package_id column is not nullable."""
        col = VulnerabilityAlert.__table__.columns["package_id"]
        assert not col.nullable

    def test_severity_has_default(self):
        """severity column has a default value of MEDIUM."""
        col = VulnerabilityAlert.__table__.columns["severity"]
        assert col.default is not None
        assert col.default.arg == "MEDIUM"

    def test_webhook_status_has_default(self):
        """webhook_status column defaults to 'pending'."""
        col = VulnerabilityAlert.__table__.columns["webhook_status"]
        assert col.default is not None
        assert col.default.arg == "pending"

    def test_package_id_indexed(self):
        """package_id column is indexed."""
        idx_names = {i.name for i in VulnerabilityAlert.__table__.indexes}
        assert any("package_id" in name for name in idx_names) or any(
            len(i.columns) == 1 and "package_id" in (c.name for c in i.columns)
            for i in VulnerabilityAlert.__table__.indexes
        )

    def test_created_at_indexed(self):
        """created_at column is indexed."""
        idx_names = {i.name for i in VulnerabilityAlert.__table__.indexes}
        assert any("created_at" in name for name in idx_names) or any(
            len(i.columns) == 1 and "created_at" in (c.name for c in i.columns)
            for i in VulnerabilityAlert.__table__.indexes
        )

    def test_package_id_foreign_key(self):
        """package_id references the packages table."""
        fks = VulnerabilityAlert.__table__.foreign_keys
        pk_fk = {fk.parent.name: fk for fk in fks}
        assert "package_id" in pk_fk
        assert pk_fk["package_id"].column.table.name == "packages"


# ---------------------------------------------------------------------------
# Behavioral tests — CRUD operations, querying, edge cases
# ---------------------------------------------------------------------------


class TestBehavioralAlertCRUD:
    """CRUD operations on VulnerabilityAlert."""

    def setup_method(self):
        reset_db()

    def _make_session(self) -> Session:
        return SessionLocal()

    def test_create_alert(self):
        """Create a VulnerabilityAlert record and verify it persists."""
        session = self._make_session()
        try:
            alert = VulnerabilityAlert(
                package_id=1,
                vuln_id="GHSA-xxxx-xxxx-xxxx",
                severity="HIGH",
                score=7.5,
                details='{"summary": "Test vuln"}',
                webhook_status="sent",
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            assert alert.id is not None
            assert alert.package_id == 1
            assert alert.vuln_id == "GHSA-xxxx-xxxx-xxxx"
            assert alert.severity == "HIGH"
            assert alert.score == 7.5
            assert alert.details == '{"summary": "Test vuln"}'
            assert alert.webhook_status == "sent"
            assert isinstance(alert.created_at, datetime)
        finally:
            session.close()

    def test_create_alert_with_defaults(self):
        """Creating an alert with minimal fields applies sensible defaults."""
        session = self._make_session()
        try:
            alert = VulnerabilityAlert(
                package_id=2,
                vuln_id="GHSA-yyyy-yyyy-yyyy",
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            assert alert.severity == "MEDIUM"  # default
            assert alert.score is None
            assert alert.webhook_status == "pending"  # default
            assert alert.created_at is not None
        finally:
            session.close()

    def test_query_by_package_id(self):
        """Alerts can be queried by package_id."""
        session = self._make_session()
        try:
            for i, sev in enumerate(["LOW", "MEDIUM", "HIGH", "CRITICAL"]):
                session.add(
                    VulnerabilityAlert(
                        package_id=10,
                        vuln_id=f"GHSA-pkg10-{i:04d}",
                        severity=sev,
                    )
                )
            # Add a different package
            session.add(
                VulnerabilityAlert(package_id=20, vuln_id="GHSA-other-0001")
            )
            session.commit()

            results = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.package_id == 10)
                .all()
            )
            assert len(results) == 4
            for r in results:
                assert r.package_id == 10
        finally:
            session.close()

    def test_query_by_severity(self):
        """Alerts can be filtered by severity level."""
        session = self._make_session()
        try:
            for i, sev in enumerate(["LOW", "MEDIUM", "HIGH", "CRITICAL"]):
                session.add(
                    VulnerabilityAlert(
                        package_id=30,
                        vuln_id=f"GHSA-sev-{i:04d}",
                        severity=sev,
                    )
                )
            session.commit()

            critical = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.severity == "CRITICAL")
                .all()
            )
            assert len(critical) == 1
            assert critical[0].vuln_id == "GHSA-sev-0003"
        finally:
            session.close()

    def test_query_by_date_range(self):
        """Alerts can be queried by created_at date range."""
        session = self._make_session()
        try:
            now = datetime.now(UTC)
            for i in range(3):
                session.add(
                    VulnerabilityAlert(
                        package_id=40,
                        vuln_id=f"GHSA-date-{i:04d}",
                        created_at=now,
                    )
                )
            session.commit()

            from_datetime = now.replace(hour=0, minute=0, second=0)
            to_datetime = now.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            results = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.created_at.between(from_datetime, to_datetime))
                .all()
            )
            assert len(results) == 3
        finally:
            session.close()

    def test_combined_package_and_severity_filter(self):
        """Alerts can be filtered by both package and severity."""
        session = self._make_session()
        try:
            for pkg_id in [50, 60]:
                for sev in ["LOW", "HIGH"]:
                    session.add(
                        VulnerabilityAlert(
                            package_id=pkg_id,
                            vuln_id=f"GHSA-combo-{pkg_id}-{sev}",
                            severity=sev,
                        )
                    )
            session.commit()

            results = (
                session.query(VulnerabilityAlert)
                .filter(
                    VulnerabilityAlert.package_id == 50,
                    VulnerabilityAlert.severity == "HIGH",
                )
                .all()
            )
            assert len(results) == 1
            assert results[0].vuln_id == "GHSA-combo-50-HIGH"
        finally:
            session.close()

    def test_delete_alert(self):
        """Alerts can be deleted."""
        session = self._make_session()
        try:
            alert = VulnerabilityAlert(
                package_id=70,
                vuln_id="GHSA-delete-0001",
            )
            session.add(alert)
            session.commit()
            alert_id = alert.id

            session.delete(alert)
            session.commit()

            gone = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.id == alert_id)
                .first()
            )
            assert gone is None
        finally:
            session.close()


class TestBehavioralAlertIndexes:
    """Verify indexes work correctly on vulnerability_alerts."""

    def setup_method(self):
        reset_db()

    def test_package_id_index_exists_in_db(self):
        """The package_id index exists at the database level."""
        engine = SessionLocal().get_bind()
        inspector = inspect(engine)
        indexes = inspector.get_indexes("vulnerability_alerts")
        index_cols = set()
        for idx in indexes:
            index_cols.update(idx["column_names"])
        assert "package_id" in index_cols

    def test_created_at_index_exists_in_db(self):
        """The created_at index exists at the database level."""
        engine = SessionLocal().get_bind()
        inspector = inspect(engine)
        indexes = inspector.get_indexes("vulnerability_alerts")
        index_cols = set()
        for idx in indexes:
            index_cols.update(idx["column_names"])
        assert "created_at" in index_cols
