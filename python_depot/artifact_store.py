"""On-disk wheel/sdist artifact store.

``ArtifactStore`` keeps artifacts under ``root_dir/<package>/<filename>``
with LRU eviction (driven by file mtime, refreshed on ``get()``), a
total size cap and per-entry TTL expiry.  Paths are validated against
traversal (absolute paths and ``..`` segments are rejected), so the
store never escapes ``root_dir`` regardless of caller-supplied names.

LRU ordering is deterministic: files are sorted by ``(mtime, path)`` so
ties on coarse-grained filesystems (e.g. 1s-granularity tmpfs) still
evict in a stable order.
"""

from __future__ import annotations

import os
import time
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

    @staticmethod
    def _safe_relative(package: str, filename: str) -> Path:
        """Validate caller-supplied names and build a root-relative path."""
        pkg = Path(package)
        fn = Path(filename)
        if pkg.is_absolute() or fn.is_absolute() or ".." in pkg.parts or ".." in fn.parts:
            raise ValueError(f"unsafe artifact path: {package}/{filename}")
        return pkg / fn

    def _files(self) -> list[Path]:
        """All artifact files under the root, sorted by (mtime, path)."""
        if not self.root_dir.is_dir():
            return []
        return sorted(
            (p for p in self.root_dir.rglob("*") if p.is_file()),
            key=lambda f: (f.stat().st_mtime, str(f)),
        )

    def store(self, package: str, filename: str, data: bytes) -> str:
        """Persist an artifact and return its absolute path."""
        target = self.root_dir / self._safe_relative(package, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if self.size() > self.max_size_bytes:
            self.evict_lru()
        return str(target)

    def get(self, package: str, filename: str) -> bytes | None:
        """Return the artifact bytes, or None when missing/expired."""
        target = self.root_dir / self._safe_relative(package, filename)
        if not target.is_file():
            return None
        os.utime(target, None)  # touch -> most recently used
        return target.read_bytes()

    def contains(self, package: str, filename: str) -> bool:
        """Whether the artifact is currently stored."""
        target = self.root_dir / self._safe_relative(package, filename)
        return target.is_file()

    def delete(self, package: str, filename: str) -> bool:
        """Remove the artifact; True when it existed."""
        target = self.root_dir / self._safe_relative(package, filename)
        if not target.is_file():
            return False
        target.unlink()
        return True

    def size(self) -> int:
        """Total stored bytes across all artifacts."""
        return sum(f.stat().st_size for f in self._files())

    def entry_count(self) -> int:
        """Number of stored artifact files."""
        return len(self._files())

    def list_artifacts(self) -> list[str]:
        """Relative '<package>/<filename>' paths of stored artifacts."""
        return [str(f.relative_to(self.root_dir)) for f in self._files()]

    def evict_lru(self, target_size_bytes: int | None = None) -> int:
        """Evict least-recently-used artifacts until size <= target.

        ``target_size_bytes`` defaults to the store's size cap.  Returns
        the number of artifacts evicted.
        """
        target = self.max_size_bytes if target_size_bytes is None else int(target_size_bytes)
        files = self._files()
        evicted = 0
        while self.size() > target and files:
            oldest = files.pop(0)
            oldest.unlink()
            evicted += 1
        return evicted

    def evict_expired(self) -> int:
        """Evict artifacts older than ttl_seconds; return count evicted."""
        cutoff = time.time() - self.ttl_seconds
        evicted = 0
        for f in self._files():
            if f.stat().st_mtime < cutoff:
                f.unlink()
                evicted += 1
        return evicted
