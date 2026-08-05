"""On-disk wheel/sdist artifact store (pre-dev stub).

``ArtifactStore`` keeps artifacts under ``root_dir/<package>/<filename>``
with LRU eviction, a total size cap and per-entry TTL expiry. Constructor
plumbing (attribute storage + root dir creation) is real so interface
tests pass immediately; every behavioral method raises
``NotImplementedError`` until the developer implements this module.
"""

from __future__ import annotations

from pathlib import Path

from python_depot.pep503_cache import DEFAULT_MAX_CACHE_BYTES, DEFAULT_TTL_SECONDS

__all__ = ["ArtifactStore"]


class ArtifactStore:
    """Cache of wheel/sdist artifact bytes with LRU, size cap and TTL."""

    def __init__(
        self,
        root_dir: str | Path,
        max_size_bytes: int = DEFAULT_MAX_CACHE_BYTES,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.max_size_bytes = int(max_size_bytes)
        self.ttl_seconds = int(ttl_seconds)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def store(self, package: str, filename: str, data: bytes) -> str:
        """Persist an artifact and return its absolute path."""
        raise NotImplementedError

    def get(self, package: str, filename: str) -> bytes | None:
        """Return the artifact bytes, or None when missing/expired."""
        raise NotImplementedError

    def contains(self, package: str, filename: str) -> bool:
        """Whether the artifact is currently stored."""
        raise NotImplementedError

    def delete(self, package: str, filename: str) -> bool:
        """Remove the artifact; True when it existed."""
        raise NotImplementedError

    def size(self) -> int:
        """Total stored bytes across all artifacts."""
        raise NotImplementedError

    def entry_count(self) -> int:
        """Number of stored artifact files."""
        raise NotImplementedError

    def list_artifacts(self) -> list[str]:
        """Relative '<package>/<filename>' paths of stored artifacts."""
        raise NotImplementedError

    def evict_lru(self, target_size_bytes: int | None = None) -> int:
        """Evict least-recently-used artifacts until size <= target."""
        raise NotImplementedError

    def evict_expired(self) -> int:
        """Evict artifacts older than ttl_seconds; return count evicted."""
        raise NotImplementedError
