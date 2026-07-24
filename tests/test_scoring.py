"""Pre-dev tests for CVSS severity scoring.

Pattern:
- Interface tests: verify imports and function signatures — PASS immediately.
- Behavioral tests: verify scoring behavior — FAIL with NotImplementedError.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, signatures)
# ---------------------------------------------------------------------------


class TestScoringInterface:
    """Verify scoring functions exist with expected signatures."""

    def test_calculate_severity_import(self):
        """calculate_severity can be imported."""
        from python_depot.dependency_health.scoring import calculate_severity

        assert callable(calculate_severity)

    def test_aggregate_score_import(self):
        """aggregate_score can be imported."""
        from python_depot.dependency_health.scoring import aggregate_score

        assert callable(aggregate_score)

    def test_calculate_severity_signature(self):
        """calculate_severity accepts cvss_vector string."""
        import inspect

        from python_depot.dependency_health.scoring import calculate_severity

        sig = inspect.signature(calculate_severity)
        assert "cvss_vector" in sig.parameters

    def test_aggregate_score_signature(self):
        """aggregate_score accepts vulns list."""
        import inspect

        from python_depot.dependency_health.scoring import aggregate_score

        sig = inspect.signature(aggregate_score)
        assert "vulns" in sig.parameters

    def test_calculate_severity_returns_dict(self):
        """calculate_severity return type is dict."""
        from typing import get_type_hints

        from python_depot.dependency_health.scoring import calculate_severity

        hints = get_type_hints(calculate_severity)
        assert "return" in hints

    def test_aggregate_score_returns_dict(self):
        """aggregate_score return type is dict."""
        from typing import get_type_hints

        from python_depot.dependency_health.scoring import aggregate_score

        hints = get_type_hints(aggregate_score)
        assert "return" in hints

    def test_both_functions_in_module(self):
        """Module exposes both functions at top level."""
        import python_depot.dependency_health.scoring as scoring

        assert hasattr(scoring, "calculate_severity")
        assert hasattr(scoring, "aggregate_score")


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestScoringBehavioral:
    """Behavioral tests for scoring — fail with NotImplementedError."""

    def test_calculate_severity_parses_cvss_v31(self):
        """Parses a valid CVSS v3.1 vector and returns score and severity."""
        from python_depot.dependency_health.scoring import calculate_severity

        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        result = calculate_severity(vector)
        assert isinstance(result, dict)
        assert "score" in result
        assert "severity" in result
        assert "vector" in result
        assert result["vector"] == vector
        assert isinstance(result["score"], float)
        assert result["severity"] in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_critical_severity(self):
        """CVSS score 9.0-10.0 is classified as CRITICAL."""
        from python_depot.dependency_health.scoring import calculate_severity

        result = calculate_severity(
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        )
        assert result["score"] >= 9.0
        assert result["severity"] == "CRITICAL"

    def test_high_severity(self):
        """CVSS score 7.0-8.9 is classified as HIGH."""
        from python_depot.dependency_health.scoring import calculate_severity

        result = calculate_severity(
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"
        )
        assert 7.0 <= result["score"] <= 8.9
        assert result["severity"] == "HIGH"

    def test_medium_severity(self):
        """CVSS score 4.0-6.9 is classified as MEDIUM."""
        from python_depot.dependency_health.scoring import calculate_severity

        result = calculate_severity(
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L"
        )
        assert 4.0 <= result["score"] <= 6.9
        assert result["severity"] == "MEDIUM"

    def test_low_severity(self):
        """CVSS score 0.1-3.9 is classified as LOW."""
        from python_depot.dependency_health.scoring import calculate_severity

        result = calculate_severity(
            "CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N"
        )
        assert 0.1 <= result["score"] <= 3.9
        assert result["severity"] == "LOW"

    def test_none_severity(self):
        """CVSS score 0.0 is classified as NONE."""
        from python_depot.dependency_health.scoring import calculate_severity

        result = calculate_severity(
            "CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:N/I:N/A:N"
        )
        assert result["score"] == 0.0
        assert result["severity"] == "NONE"

    def test_invalid_vector_raises_value_error(self):
        """Malformed CVSS vector raises ValueError."""
        from python_depot.dependency_health.scoring import calculate_severity

        with pytest.raises(ValueError):
            calculate_severity("not-a-valid-vector")

    def test_empty_vector_raises_value_error(self):
        """Empty CVSS vector raises ValueError."""
        from python_depot.dependency_health.scoring import calculate_severity

        with pytest.raises(ValueError):
            calculate_severity("")

    def test_aggregate_score_single_vuln(self):
        """Aggregate score for a single vulnerability returns correct values."""
        from python_depot.dependency_health.scoring import aggregate_score

        vulns = [
            {"id": "GHSA-xxxx", "severity": "HIGH", "score": 7.5, "fixed": True}
        ]
        result = aggregate_score(vulns)
        assert isinstance(result, dict)
        assert "total" in result
        assert "max_severity" in result
        assert "vuln_count" in result
        assert result["vuln_count"] == 1
        assert result["max_severity"] == "HIGH"

    def test_aggregate_score_multiple_vulns(self):
        """Aggregate score for multiple vulns picks highest severity."""
        from python_depot.dependency_health.scoring import aggregate_score

        vulns = [
            {"id": "GHSA-aaa", "severity": "LOW", "score": 2.5},
            {"id": "GHSA-bbb", "severity": "CRITICAL", "score": 9.8},
            {"id": "GHSA-ccc", "severity": "MEDIUM", "score": 5.0},
        ]
        result = aggregate_score(vulns)
        assert result["vuln_count"] == 3
        assert result["max_severity"] == "CRITICAL"
        assert "breakdown" in result

    def test_aggregate_score_breakdown(self):
        """Aggregate score includes per-severity breakdown."""
        from python_depot.dependency_health.scoring import aggregate_score

        vulns = [
            {"id": "GHSA-aaa", "severity": "CRITICAL", "score": 9.8},
            {"id": "GHSA-bbb", "severity": "HIGH", "score": 7.5},
        ]
        result = aggregate_score(vulns)
        breakdown = result["breakdown"]
        assert breakdown.get("CRITICAL") == 1
        assert breakdown.get("HIGH") == 1

    def test_aggregate_score_empty_raises_value_error(self):
        """Empty vulns list raises ValueError."""
        from python_depot.dependency_health.scoring import aggregate_score

        with pytest.raises(ValueError):
            aggregate_score([])

    def test_aggregate_score_avg_score_calculated(self):
        """Aggregate score includes average CVSS score."""
        from python_depot.dependency_health.scoring import aggregate_score

        vulns = [
            {"id": "GHSA-aaa", "severity": "HIGH", "score": 7.5},
            {"id": "GHSA-bbb", "severity": "MEDIUM", "score": 5.5},
        ]
        result = aggregate_score(vulns)
        assert "avg_score" in result
        assert result["avg_score"] == 6.5
