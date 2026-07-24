"""CVSS severity scoring — CVSS v3.1 base score calculation.

Provides CVSS v3.1 score calculation and severity classification
based on vulnerability data from OSV.dev responses.
"""
from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------------------
# CVSS v3.1 metric weights
# ---------------------------------------------------------------------------

# Attack Vector (AV)
AV: dict[str, float] = {
    "N": 0.85,  # Network
    "A": 0.62,  # Adjacent
    "L": 0.55,  # Local
    "P": 0.20,  # Physical
}

# Attack Complexity (AC)
AC: dict[str, float] = {
    "L": 0.77,  # Low
    "H": 0.44,  # High
}

# Privileges Required (PR) — depends on Scope
PR_UNCHANGED: dict[str, float] = {
    "N": 0.85,
    "L": 0.62,
    "H": 0.27,
}
PR_CHANGED: dict[str, float] = {
    "N": 0.85,
    "L": 0.68,
    "H": 0.50,
}

# User Interaction (UI)
UI: dict[str, float] = {
    "N": 0.85,
    "R": 0.62,
}

# Confidentiality / Integrity / Availability Impact (C, I, A)
CIA: dict[str, float] = {
    "N": 0.00,  # None
    "L": 0.22,  # Low
    "H": 0.56,  # High
}

# Severity thresholds (upper bound inclusive)
SEVERITY_RANGES: list[tuple[float, str]] = [
    (0.0, "NONE"),
    (3.9, "LOW"),
    (6.9, "MEDIUM"),
    (8.9, "HIGH"),
    (10.0, "CRITICAL"),
]

# Regex for a CVSS v3.1 vector string
CVSS_VECTOR_RE = re.compile(
    r"^CVSS:3\.1/"
    r"AV:([NALP])/"
    r"AC:([LH])/"
    r"PR:([NLH])/"
    r"UI:([NR])/"
    r"S:([UC])/"
    r"C:([NLH])/"
    r"I:([NLH])/"
    r"A:([NLH])$"
)


def _round_to_1_decimal(value: float) -> float:
    """Round to 1 decimal place using CVSS standard (half-up)."""
    return round(value * 10.0) / 10.0


def calculate_severity(cvss_vector: str) -> dict[str, Any]:
    """Parse a CVSS v3.1 vector string and compute base score and severity.

    Implements the CVSS v3.1 base score formula as published by FIRST.org.

    Args:
        cvss_vector: CVSS v3.1 vector string
                     (e.g. 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H').

    Returns:
        Dict with:
            - 'score' (float): Base score 0.0-10.0
            - 'severity' (str): 'NONE', 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
            - 'vector' (str): The original vector string

    Raises:
        ValueError: If the vector string is malformed or unparseable.
    """
    if not cvss_vector or not cvss_vector.strip():
        raise ValueError("CVSS vector string is empty")

    match = CVSS_VECTOR_RE.match(cvss_vector.strip())
    if not match:
        raise ValueError(
            f"Invalid CVSS v3.1 vector: '{cvss_vector}'. "
            "Expected format: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        )

    av, ac, pr, ui, s, c_imp, i_imp, a_imp = match.groups()

    # Metric values
    av_val = AV[av]
    ac_val = AC[ac]
    pr_val = PR_CHANGED[pr] if s == "C" else PR_UNCHANGED[pr]
    ui_val = UI[ui]
    c_val = CIA[c_imp]
    i_val = CIA[i_imp]
    a_val = CIA[a_imp]

    # Impact Sub-Score (ISS)
    iss = 1.0 - (1.0 - c_val) * (1.0 - i_val) * (1.0 - a_val)

    # Impact Score
    if s == "C":  # Scope Changed
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    else:  # Scope Unchanged
        impact = 6.42 * iss

    # Exploitability Score
    exploitability = 8.22 * av_val * ac_val * pr_val * ui_val

    # Base Score
    if impact <= 0:
        base_score = 0.0
    elif s == "C":  # Scope Changed
        base_score = min(1.08 * (impact + exploitability), 10.0)
    else:  # Scope Unchanged
        base_score = min(impact + exploitability, 10.0)

    base_score = _round_to_1_decimal(base_score)

    # Classify severity
    severity: str = "NONE"
    for threshold, label in SEVERITY_RANGES:
        if base_score <= threshold:
            severity = label
            break

    return {
        "score": base_score,
        "severity": severity,
        "vector": cvss_vector.strip(),
    }


def aggregate_score(vulns: list[dict]) -> dict[str, Any]:
    """Aggregate multiple vulnerability scores into a package health score.

    The composite score considers:
    - Highest severity among all vulnerabilities
    - Total vulnerability count
    - Average CVSS score
    - Whether fixes are available

    Args:
        vulns: List of vulnerability dicts, each expected to contain
               at least 'severity' and optionally 'score' and 'fixed'.

    Returns:
        Dict with:
            - 'total' (float): Composite score 0.0-10.0 (higher = worse)
            - 'max_severity' (str): Highest severity found
            - 'vuln_count' (int): Number of vulnerabilities evaluated
            - 'avg_score' (float): Average CVSS base score
            - 'breakdown' (dict): Per-severity counts (CRITICAL, HIGH, etc.)

    Raises:
        ValueError: If vulns list is empty or contains invalid entries.
    """
    if not vulns:
        raise ValueError("vulnerabilities list is empty, cannot aggregate")

    severity_order = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

    max_severity: str = "NONE"
    total_score: float = 0.0
    scored_count: int = 0
    breakdown: dict[str, int] = {
        "NONE": 0,
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    for vuln in vulns:
        sev = vuln.get("severity", "NONE")
        if sev not in breakdown:
            raise ValueError(f"Invalid severity level: {sev}")
        breakdown[sev] += 1

        # Track highest severity
        if severity_order.index(sev) > severity_order.index(max_severity):
            max_severity = sev

        # Track average score
        score = vuln.get("score")
        if score is not None and isinstance(score, (int, float)):
            total_score += float(score)
            scored_count += 1

    avg_score = round(total_score / scored_count, 2) if scored_count > 0 else 0.0

    # Total composite score: weighted combination of average score and max severity
    # This gives a 0-10 representation of the overall vulnerability posture
    severity_bonus = severity_order.index(max_severity) * 1.5
    total = round(min(avg_score + severity_bonus, 10.0), 1)

    return {
        "total": total,
        "max_severity": max_severity,
        "vuln_count": len(vulns),
        "avg_score": avg_score,
        "breakdown": breakdown,
    }
