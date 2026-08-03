"""Supply-chain typosquatting scanner.

Detects typosquatting and malicious-package risk for PyPI packages:

- ``SimilarityEngine``: Levenshtein / Damerau-Levenshtein edit distance,
  prefix/suffix heuristics, and a configurable similarity threshold used
  to decide whether a candidate name typosquats a known package.
- ``MaliciousFeed``: OSV entries plus an optional curated blocklist,
  loaded lazily and refreshed by a fresh scan.
- ``SupplyChainScanner``: combines name similarity, feed membership,
  download count and release freshness into an integer 0-100 score.
- ``SupplyChainAlerter``: fires webhook notifications for newly
  detected suspicious packages exactly once (DB-backed dedup).
- ``fetch_package_info``: real PyPI metadata (downloads, release date)
  feeding the heuristics — unknown data is never guessed.
- ``store_verdict`` / ``store_verdicts`` / ``list_verdicts``: SQLite
  persistence via the ``SupplyChainVerdict`` model (batch upsert).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from python_depot.models.supply_chain_verdict import SupplyChainVerdict

logger = logging.getLogger(__name__)

__all__ = [
    "SimilarityEngine",
    "PackageInfo",
    "MaliciousFeed",
    "SupplyChainScanner",
    "SupplyChainAlerter",
    "fetch_package_info",
    "store_verdict",
    "store_verdicts",
    "list_verdicts",
]

# Upper bound for package names accepted by the similarity engine. The
# Damerau-Levenshtein matrix is O(n*m) — an unbounded name would let an
# unauthenticated caller CPU-amplify the async event loop (F1).
MAX_NAME_LENGTH = 200

# Real PyPI metadata sources for the download/freshness heuristics.
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
PYPI_STATS_URL = "https://pypistats.org/api/packages/{name}/recent"
METADATA_TIMEOUT = 10.0  # seconds

# Top-N popular PyPI packages used as the typosquatting comparison corpus.
# A candidate name similar to one of these (but not identical) is flagged.
POPULAR_PACKAGES: list[str] = [
    "requests",
    "numpy",
    "pandas",
    "django",
    "flask",
    "tornado",
    "scipy",
    "matplotlib",
    "pip",
    "setuptools",
    "urllib3",
    "aiohttp",
    "boto3",
    "six",
    "click",
    "jinja2",
    "pyyaml",
    "sqlalchemy",
    "fastapi",
    "pydantic",
]


class SimilarityEngine:
    """Name-similarity heuristics for typosquatting detection.

    Combines Levenshtein / Damerau-Levenshtein edit distance with
    prefix/suffix heuristics into a normalized similarity score in
    [0.0, 1.0]; ``is_similar`` compares that score against the
    configurable ``threshold``.
    """

    def __init__(self, threshold: float = 0.8) -> None:
        """Initialize the engine.

        Args:
            threshold: Minimum similarity score (0.0-1.0) for a candidate
                       name to be considered a typosquat of a known name.
        """
        self.threshold = threshold

    @staticmethod
    def _validate_length(a: str, b: str) -> None:
        """Reject inputs longer than MAX_NAME_LENGTH (CPU-amplification guard).

        The distance matrix is O(n*m); an unbounded name would let a
        caller stall the async event loop. Raises ValueError — the app
        maps ValueError to HTTP 422 (see api.py).
        """
        if len(a) > MAX_NAME_LENGTH or len(b) > MAX_NAME_LENGTH:
            raise ValueError(
                f"package name exceeds max length {MAX_NAME_LENGTH}"
            )

    def levenshtein_distance(self, a: str, b: str) -> int:
        """Return the Levenshtein edit distance between two names."""
        self._validate_length(a, b)
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)

        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            curr = [i]
            for j, cb in enumerate(b, start=1):
                cost = 0 if ca == cb else 1
                curr.append(
                    min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
                )
            prev = curr
        return prev[-1]

    def damerau_levenshtein_distance(self, a: str, b: str) -> int:
        """Return the Damerau-Levenshtein distance (incl. transpositions).

        Uses optimal string alignment (restricted edit distance): adjacent
        transpositions count as a single edit.
        """
        self._validate_length(a, b)
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)

        len_a, len_b = len(a), len(b)
        # Distance matrix with (i, j) = distance between a[:i] and b[:j]
        d = [[0] * (len_b + 1) for _ in range(len_a + 1)]
        for i in range(len_a + 1):
            d[i][0] = i
        for j in range(len_b + 1):
            d[0][j] = j

        for i in range(1, len_a + 1):
            for j in range(1, len_b + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                d[i][j] = min(
                    d[i - 1][j] + 1,  # deletion
                    d[i][j - 1] + 1,  # insertion
                    d[i - 1][j - 1] + cost,  # substitution
                )
                if (
                    i > 1
                    and j > 1
                    and a[i - 1] == b[j - 2]
                    and a[i - 2] == b[j - 1]
                ):
                    d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)  # transposition
        return d[len_a][len_b]

    def prefix_similarity(self, a: str, b: str) -> float:
        """Return a [0.0, 1.0] score based on shared prefix length."""
        if not a or not b:
            return 0.0
        shared = 0
        for ca, cb in zip(a, b):
            if ca != cb:
                break
            shared += 1
        return shared / max(len(a), len(b))

    def suffix_similarity(self, a: str, b: str) -> float:
        """Return a [0.0, 1.0] score based on shared suffix length."""
        if not a or not b:
            return 0.0
        shared = 0
        for ca, cb in zip(reversed(a), reversed(b)):
            if ca != cb:
                break
            shared += 1
        return shared / max(len(a), len(b))

    def similarity(self, a: str, b: str) -> float:
        """Return the combined normalized similarity score in [0.0, 1.0].

        Combines normalized edit distance with prefix/suffix heuristics by
        taking the strongest signal: a candidate that shares a long prefix
        or suffix with a known name is flagged even when the edit distance
        is relatively large (e.g. ``request`` vs ``request-toolkit``).
        """
        self._validate_length(a, b)
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        max_len = max(len(a), len(b))
        edit_sim = 1.0 - self.damerau_levenshtein_distance(a, b) / max_len
        return max(edit_sim, self.prefix_similarity(a, b), self.suffix_similarity(a, b))

    def is_similar(self, candidate: str, known: str) -> bool:
        """Return True when ``candidate`` typosquats ``known``.

        Compares the combined similarity score against ``self.threshold``.
        """
        return self.similarity(candidate, known) >= self.threshold


@dataclass
class PackageInfo:
    """Metadata about a package used by download/freshness heuristics.

    Attributes:
        name: Package name.
        downloads: Lifetime download count. ``None`` means the count is
            UNKNOWN — the scanner must not apply the download heuristic
            (no reason, no score contribution). ``0`` is a real, known
            zero. The default of 0 preserves the dataclass contract.
        released_at: First release / publish timestamp (None when unknown).
    """

    name: str
    downloads: int | None = 0
    released_at: datetime | None = None


def _parse_release_time(pypi: dict) -> datetime | None:
    """Extract the first release timestamp from a PyPI JSON response."""
    info = pypi.get("info", {})
    upload_time = info.get("upload_time")
    if not upload_time:
        urls = pypi.get("urls") or []
        if urls:
            upload_time = urls[0].get("upload_time_iso_8601")
    if not upload_time:
        return None
    try:
        return datetime.fromisoformat(str(upload_time).replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_package_info(name: str) -> PackageInfo | None:
    """Fetch real package metadata (downloads, release date) from PyPI.

    Download counts come from pypistats and release dates from the PyPI
    JSON API, each best-effort with a bounded timeout. Returns ``None``
    when the metadata cannot be retrieved at all — unknown data is NEVER
    guessed, so a failed fetch can never produce a bogus "low download
    count" reason (F2).
    """
    try:
        async with httpx.AsyncClient(
            timeout=METADATA_TIMEOUT, follow_redirects=True
        ) as client:
            resp = await client.get(PYPI_JSON_URL.format(name=name))
            resp.raise_for_status()
            pypi = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("PyPI metadata fetch failed for %s — treating as unknown", name)
        return None

    released_at = _parse_release_time(pypi)

    downloads: int | None = None
    try:
        async with httpx.AsyncClient(
            timeout=METADATA_TIMEOUT, follow_redirects=True
        ) as client:
            stats_resp = await client.get(PYPI_STATS_URL.format(name=name))
            stats_resp.raise_for_status()
            stats_data = (stats_resp.json().get("data") or {})
            last_month = stats_data.get("last_month")
            downloads = int(last_month) if last_month is not None else None
    except (httpx.HTTPError, ValueError, TypeError):
        downloads = None  # unknown — never guess

    return PackageInfo(name=name, downloads=downloads, released_at=released_at)


class MaliciousFeed:
    """Malicious package feed — OSV entries plus optional curated blocklist.

    Entries are used by the scanner both to flag known-malicious names
    directly and as the ``known`` corpus for typosquatting comparison.
    ``load`` populates state from the configured sources and ``refresh``
    re-fetches it so a fresh scan updates feed data.
    """

    def __init__(
        self,
        osv_entries: list[dict] | None = None,
        blocklist: list[str] | None = None,
    ) -> None:
        """Initialize the feed.

        Args:
            osv_entries: OSV vulnerability/package entries (list of dicts).
            blocklist: Optional curated list of known-malicious names.
        """
        self.osv_entries = osv_entries or []
        self.blocklist = blocklist or []
        self._known: set[str] = set()
        self._loaded = False

    def load(self) -> None:
        """Load feed data from the configured sources."""
        known: set[str] = set(self.blocklist)
        for entry in self.osv_entries:
            name = entry.get("package") if isinstance(entry, dict) else None
            if name:
                known.add(name)
        self._known = known
        self._loaded = True

    def refresh(self) -> None:
        """Re-fetch feed data so a fresh scan sees updated entries."""
        self.load()

    def is_known_malicious(self, name: str) -> bool:
        """Return True when ``name`` appears in the OSV/blocklist data."""
        if not self._loaded:
            self.load()
        return name in self._known

    def known_packages(self) -> list[str]:
        """Return the list of known-malicious package names."""
        if not self._loaded:
            self.load()
        return sorted(self._known)


class SupplyChainScanner:
    """Combines similarity, feed, download and freshness signals into a score.

    Produces a ``SupplyChainVerdict`` with an integer score in 0-100 and a
    list of human-readable reasons. Low download counts, recent publication
    and name similarity to a known/malicious package all raise the score.
    """

    def __init__(
        self,
        engine: SimilarityEngine | None = None,
        feed: MaliciousFeed | None = None,
        threshold: float = 0.8,
        min_downloads: int = 1000,
        max_release_age_days: int = 30,
    ) -> None:
        """Initialize the scanner.

        Args:
            engine: Similarity engine (a default is created if omitted).
            feed: Malicious package feed (a default is created if omitted).
            threshold: Similarity threshold used when no engine is given.
            min_downloads: Downloads below this count raise risk.
            max_release_age_days: Releases younger than this raise risk.
        """
        self.engine = engine or SimilarityEngine(threshold=threshold)
        self.feed = feed or MaliciousFeed()
        self.threshold = threshold
        self.min_downloads = min_downloads
        self.max_release_age_days = max_release_age_days

    def download_risk(self, downloads: int) -> float:
        """Return a [0.0, 1.0] risk contribution for a download count.

        Fewer downloads → higher risk. The curve drops off smoothly around
        ``min_downloads`` and approaches 0 for very popular packages.
        """
        if downloads <= 0:
            return 1.0
        denominator = max(1, self.min_downloads)
        return 1.0 / (1.0 + downloads / denominator)

    def freshness_risk(self, released_at: datetime | None) -> float:
        """Return a [0.0, 1.0] risk contribution for a release timestamp.

        Packages released within ``max_release_age_days`` get the full risk
        score; older releases decay linearly to 0 over the following year.
        Unknown release dates contribute no risk.
        """
        if released_at is None:
            return 0.0
        age_days = max(
            0.0, (datetime.now(UTC) - released_at).total_seconds() / 86400.0
        )
        if age_days <= self.max_release_age_days:
            return 1.0
        decay = 1.0 - (age_days - self.max_release_age_days) / 365.0
        return max(0.0, min(1.0, decay))

    def _best_typosquat(self, package: str) -> tuple[str | None, float]:
        """Return the strongest typosquat match (name, similarity) or (None, 0).

        Compares ``package`` against the feed's known-malicious names and the
        popular-PyPI corpus, ignoring the package itself.
        """
        corpus = list(dict.fromkeys(self.feed.known_packages() + POPULAR_PACKAGES))
        best_name: str | None = None
        best_score = 0.0
        for known in corpus:
            if known == package:
                continue
            score = self.engine.similarity(package, known)
            if score > best_score:
                best_score = score
                best_name = known
        return best_name, best_score

    def scan(self, package: str, info: PackageInfo | None = None) -> SupplyChainVerdict:
        """Scan a single package and return its supply-chain verdict.

        ``info`` carries real package metadata (downloads, release date).
        When omitted — or when download data is unknown (``None``) — the
        download heuristic is skipped entirely: the scanner never guesses
        (F2). The feed is NOT refreshed here; callers (``scan_many`` or
        the router) refresh once per scan run (F5).
        """
        reasons: list[str] = []
        score = 0.0

        # 1. Known-malicious membership (hard signal).
        if self.feed.is_known_malicious(package):
            score += 60
            reasons.append("package is listed as known-malicious")

        # 2. Name similarity to a known / popular package (typosquatting).
        best_name, best_score = self._best_typosquat(package)
        if best_name is not None and best_score >= self.threshold:
            score += 20
            reasons.append(f"name is similar to known package '{best_name}'")

        # 3. Download-count heuristic — real data only; unknown is never
        #    guessed (no reason, no score inflation).
        if info is not None and info.downloads is not None:
            dl_risk = self.download_risk(info.downloads)
            if dl_risk > 0.5:
                score += dl_risk * 15
                reasons.append(f"low download count ({info.downloads})")

        # 4. Release-freshness heuristic — real data only.
        if info is not None:
            fr_risk = self.freshness_risk(info.released_at)
            if fr_risk > 0.5:
                score += fr_risk * 15
                reasons.append("recently published")

        final_score = min(100, int(round(score)))
        return SupplyChainVerdict(
            package=package,
            score=final_score,
            reasons=reasons,
        )

    def scan_many(self, packages: list[str]) -> list[SupplyChainVerdict]:
        """Scan multiple packages and return one verdict per package.

        Refreshes the feed exactly once for the whole run — the per-package
        ``scan`` no longer refreshes (F5).
        """
        self.feed.refresh()
        return [self.scan(package) for package in packages]


class SupplyChainAlerter:
    """Fires notifications for newly detected suspicious packages.

    Follows the existing webhook/email notification pattern used by the
    dependency-health ``AlertEngine``: a package that was already notified
    must not trigger a second notification (exactly-once semantics).
    Dedup is DB-backed via ``SupplyChainVerdict.notified`` — it survives
    across alerter instances and requests, not just within one instance
    (F4). An in-memory set covers the ``db=None`` path.
    """

    def __init__(
        self,
        db: Session | None = None,
        webhook_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the alerter.

        Args:
            db: SQLAlchemy session used for exactly-once dedup checks.
            webhook_url: Optional webhook URL for alert delivery.
            transport: Optional httpx transport (tests inject a
                       MockTransport to observe deliveries).
        """
        self.db = db
        self.webhook_url = webhook_url
        self.transport = transport
        self._notified: set[str] = set()

    def _already_notified(self, package: str) -> bool:
        """Return True when the package has already been alerted on.

        Checks the in-memory set first, then the persistent
        ``SupplyChainVerdict.notified`` flag. A stale table without the
        column falls back to in-memory dedup (dev DBs predating the
        column are recreated by tests/app startup).
        """
        if package in self._notified:
            return True
        if self.db is not None:
            try:
                row = (
                    self.db.query(SupplyChainVerdict)
                    .filter(SupplyChainVerdict.package == package)
                    .first()
                )
                return bool(row is not None and row.notified)
            except OperationalError:
                logger.warning(
                    "Verdict table missing 'notified' column — using in-memory dedup"
                )
        return False

    def _mark_notified(self, package: str) -> None:
        """Persist the notified flag so dedup survives future requests."""
        if self.db is None:
            return
        try:
            row = (
                self.db.query(SupplyChainVerdict)
                .filter(SupplyChainVerdict.package == package)
                .first()
            )
            if row is not None:
                row.notified = True
                self.db.commit()
        except OperationalError:
            logger.warning(
                "Verdict table missing 'notified' column — skipping persistent dedup"
            )

    async def notify_new_suspicious(self, verdict: SupplyChainVerdict) -> bool:
        """Notify about a suspicious package.

        Returns True when a notification was actually sent; returns False
        when the package was already notified (dedup / exactly-once) or
        no webhook is configured.
        """
        if self._already_notified(verdict.package):
            return False
        if not self.webhook_url:
            logger.warning("No webhook URL configured — skipping alert delivery")
            return False

        payload = {
            "event": "supply_chain_alert",
            "package": verdict.package,
            "score": verdict.score,
            "reasons": verdict.reasons,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            async with httpx.AsyncClient(
                timeout=15, transport=self.transport
            ) as client:
                resp = await client.post(self.webhook_url, json=payload)
                resp.raise_for_status()
            logger.info(
                "Webhook delivered for %s (score %d): %d",
                verdict.package,
                verdict.score,
                resp.status_code,
            )
        except httpx.HTTPError as exc:
            # Log the status code only — the exception string embeds the
            # request URL, which would leak a tokenized webhook URL (F6).
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None:
                logger.error(
                    "Webhook delivery failed for %s (status %d)",
                    verdict.package,
                    status,
                )
            else:
                logger.error("Webhook delivery failed for %s", verdict.package)
            return False

        self._notified.add(verdict.package)
        self._mark_notified(verdict.package)
        return True


def store_verdicts(db: Session, verdicts: list[SupplyChainVerdict]) -> None:
    """Batch-persist verdicts in a single commit (F5).

    One SELECT IN fetches existing rows, new rows are bulk-added and a
    single COMMIT writes everything — instead of N separate
    SELECT+upsert+COMMIT round-trips. The ``notified`` flag is preserved
    on update so exactly-once alert dedup survives re-scans (F4).
    """
    if not verdicts:
        return

    packages = [v.package for v in verdicts]
    existing = {
        row.package: row
        for row in db.query(SupplyChainVerdict)
        .filter(SupplyChainVerdict.package.in_(packages))
        .all()
    }

    for verdict in verdicts:
        reasons: str | None = verdict.reasons
        if isinstance(reasons, list):
            reasons = json.dumps(reasons)

        row = existing.get(verdict.package)
        if row is not None:
            row.score = verdict.score
            row.reasons = reasons
            if verdict.detected_at is not None:
                row.detected_at = verdict.detected_at
            continue

        new_row = SupplyChainVerdict(
            package=verdict.package,
            score=verdict.score,
            reasons=reasons,
        )
        if verdict.detected_at is not None:
            new_row.detected_at = verdict.detected_at
        db.add(new_row)

    db.commit()


def store_verdict(db: Session, verdict: SupplyChainVerdict) -> None:
    """Persist a single verdict (insert or update by package)."""
    store_verdicts(db, [verdict])


def list_verdicts(db: Session) -> list[SupplyChainVerdict]:
    """Return stored verdicts, most recent first."""
    return (
        db.query(SupplyChainVerdict)
        .order_by(SupplyChainVerdict.detected_at.desc())
        .all()
    )
