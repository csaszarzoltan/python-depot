"""Pre-dev TDD tests for the on-disk artifact store.

Pattern (repo convention):
- Interface tests: verify imports, class/function signatures, type hints
  and constructor plumbing — PASS immediately.
- Behavioral tests: verify wheel/sdist artifact storage with LRU
  eviction, size cap and TTL by calling the stub methods directly —
  FAIL with NotImplementedError until the developer implements
  ``python_depot/artifact_store.py``.
"""

from __future__ import annotations

import inspect
import os
import time
from pathlib import Path

import pytest

from python_depot.artifact_store import ArtifactStore
from python_depot.pep503_cache import DEFAULT_MAX_CACHE_BYTES, DEFAULT_TTL_SECONDS


def _ret_annotation(func) -> str:
    """Return annotation as string (works with ``from __future__ import annotations``)."""
    return inspect.signature(func).return_annotation


@pytest.fixture
def store(tmp_path):
    """ArtifactStore rooted in a temp dir with a 1 GiB cap and 1h TTL."""
    return ArtifactStore(root_dir=tmp_path, max_size_bytes=1024**3, ttl_seconds=3600)


@pytest.fixture
def small_store(tmp_path):
    """ArtifactStore with a tiny 10-byte cap to force LRU eviction."""
    return ArtifactStore(root_dir=tmp_path, max_size_bytes=10, ttl_seconds=3600)


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestArtifactStoreInterface:
    """ArtifactStore class contract."""

    def test_importable(self):
        assert isinstance(ArtifactStore, type)

    def test_init_signature(self):
        """__init__ accepts root_dir, max_size_bytes and ttl_seconds."""
        sig = inspect.signature(ArtifactStore.__init__)
        params = sig.parameters
        assert "root_dir" in params
        assert "max_size_bytes" in params
        assert "ttl_seconds" in params
        assert params["max_size_bytes"].default == DEFAULT_MAX_CACHE_BYTES
        assert params["ttl_seconds"].default == DEFAULT_TTL_SECONDS

    def test_constructible_and_creates_dir(self, tmp_path):
        """Constructor plumbing: attributes stored, root dir created."""
        store = ArtifactStore(root_dir=tmp_path / "artifacts", max_size_bytes=1000, ttl_seconds=60)
        assert store.root_dir == tmp_path / "artifacts"
        assert store.max_size_bytes == 1000
        assert store.ttl_seconds == 60
        assert (tmp_path / "artifacts").is_dir()

    def test_has_all_methods(self):
        """Every documented store method exists."""
        for name in (
            "store",
            "get",
            "contains",
            "delete",
            "size",
            "entry_count",
            "list_artifacts",
            "evict_lru",
            "evict_expired",
        ):
            assert callable(getattr(ArtifactStore, name)), name

    def test_store_signature(self):
        """store(package, filename, data) -> str."""
        sig = inspect.signature(ArtifactStore.store)
        for param in ("package", "filename", "data"):
            assert param in sig.parameters
        ret = _ret_annotation(ArtifactStore.store)
        assert ret == "str" or ret is str

    def test_get_signature(self):
        """get(package, filename) -> bytes | None."""
        sig = inspect.signature(ArtifactStore.get)
        assert "package" in sig.parameters
        assert "filename" in sig.parameters
        ret = _ret_annotation(ArtifactStore.get)
        assert "bytes" in str(ret) and "None" in str(ret)

    def test_evict_method_signatures(self):
        """evict_lru/evict_expired return int."""
        assert _ret_annotation(ArtifactStore.evict_lru) in ("int", int)
        assert _ret_annotation(ArtifactStore.evict_expired) in ("int", int)

    def test_list_artifacts_returns_list(self):
        """list_artifacts returns list[str]."""
        assert _ret_annotation(ArtifactStore.list_artifacts) in ("list[str]", list)


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestArtifactStoreBehavioral:
    """Wheel/sdist artifact storage."""

    def test_store_writes_file_and_returns_path(self, store):
        """store() persists bytes under root_dir/<package>/<filename>."""
        path = store.store("requests", "requests-2.32.0-py3-none-any.whl", b"wheel-bytes")
        assert Path(path) == store.root_dir / "requests" / "requests-2.32.0-py3-none-any.whl"
        assert Path(path).is_file()
        assert Path(path).read_bytes() == b"wheel-bytes"

    def test_get_returns_stored_bytes(self, store):
        """get() round-trips the stored bytes."""
        store.store("requests", "requests-2.32.0-py3-none-any.whl", b"wheel-bytes")
        assert store.get("requests", "requests-2.32.0-py3-none-any.whl") == b"wheel-bytes"

    def test_get_missing_returns_none(self, store):
        """get() returns None for an unknown artifact."""
        assert store.get("requests", "no-such-file.whl") is None

    def test_contains_after_store(self, store):
        """contains() reflects stored artifacts."""
        store.store("numpy", "numpy-2.0.0-cp312-cp312-manylinux_2_17_x86_64.whl", b"x")
        assert store.contains("numpy", "numpy-2.0.0-cp312-cp312-manylinux_2_17_x86_64.whl")
        assert not store.contains("numpy", "missing.whl")
        assert not store.contains("requests", "numpy-2.0.0-cp312-cp312-manylinux_2_17_x86_64.whl")

    def test_delete_removes_artifact(self, store):
        """delete() removes the artifact and reports it."""
        store.store("requests", "x.whl", b"data")
        assert store.delete("requests", "x.whl") is True
        assert not store.contains("requests", "x.whl")
        assert store.delete("requests", "x.whl") is False

    def test_size_tracks_total_bytes(self, store):
        """size() sums stored artifact bytes."""
        store.store("a", "f1.whl", b"12345")
        store.store("b", "f2.tar.gz", b"1234567")
        assert store.size() == 12

    def test_entry_count_tracks_files(self, store):
        """entry_count() counts stored artifact files."""
        store.store("a", "f1.whl", b"1")
        store.store("b", "f2.tar.gz", b"12")
        assert store.entry_count() == 2

    def test_list_artifacts_lists_relative_paths(self, store):
        """list_artifacts() returns <package>/<filename> entries."""
        store.store("a", "f1.whl", b"1")
        store.store("b", "f2.tar.gz", b"12")
        listed = set(store.list_artifacts())
        assert "a/f1.whl" in listed
        assert "b/f2.tar.gz" in listed


class TestLruEvictionBehavioral:
    """LRU eviction and size cap."""

    def test_evict_lru_removes_least_recently_used(self, small_store):
        """Eviction under pressure removes the least-recently-used artifact first."""
        small_store.store("a", "f1.whl", b"12345")
        small_store.store("a", "f2.whl", b"12345")
        small_store.store("a", "f3.whl", b"12345")
        small_store.store("a", "f4.whl", b"12345")  # 20 > 10 → auto-evict down to 10
        assert small_store.size() <= small_store.max_size_bytes
        small_store.get("a", "f3.whl")  # touch f3 → f4 is now LRU
        evicted = small_store.evict_lru(target_size_bytes=5)
        assert evicted >= 1
        assert not small_store.contains("a", "f4.whl")  # LRU evicted
        assert small_store.contains("a", "f3.whl")      # most recent survives
        assert small_store.size() <= 5

    def test_evict_lru_under_cap_evicts_nothing(self, store):
        """No eviction when the store is within the size cap."""
        store.store("a", "f1.whl", b"12345")
        assert store.evict_lru() == 0

    def test_store_respects_size_cap(self, small_store):
        """After stores beyond the cap, size never exceeds max_size_bytes."""
        small_store.store("a", "f1.whl", b"12345")
        small_store.store("a", "f2.whl", b"12345")
        small_store.store("a", "f3.whl", b"12345")
        small_store.store("a", "f4.whl", b"12345")
        assert small_store.size() <= small_store.max_size_bytes

    def test_evict_lru_accepts_custom_target(self, small_store):
        """evict_lru(target) evicts down to an explicit byte ceiling."""
        small_store.store("a", "f1.whl", b"12345")
        small_store.store("a", "f2.whl", b"12345")
        evicted = small_store.evict_lru(target_size_bytes=5)
        assert evicted >= 1
        assert small_store.size() <= 5

    def test_get_refreshes_lru_order(self, small_store):
        """A get() makes an artifact the most recently used."""
        small_store.store("a", "f2.whl", b"12345")
        small_store.store("a", "f1.whl", b"12345")
        base = small_store.root_dir / "a"
        # Pin explicit mtimes: tmpfs can have 1s granularity, which would make
        # the LRU order ambiguous (ties) and the eviction target nondeterministic.
        # The pins use recent timestamps so the files stay inside the TTL
        # window — get() now enforces per-entry TTL expiry lazily.
        now = time.time()
        os.utime(base / "f2.whl", (now - 60, now - 60))
        os.utime(base / "f1.whl", (now - 50, now - 50))
        small_store.store("a", "f3.whl", b"12345")  # over cap → LRU (f2) evicted
        assert not small_store.contains("a", "f2.whl")
        small_store.get("a", "f1.whl")  # touch f1 → now most recent
        small_store.evict_lru(target_size_bytes=5)  # must evict f3, keep f1
        assert not small_store.contains("a", "f3.whl")
        assert small_store.contains("a", "f1.whl")


class TestTtlEvictionBehavioral:
    """TTL expiry of stale artifacts."""

    def test_evict_expired_removes_stale_entries(self, store):
        """Entries older than ttl_seconds are evicted by evict_expired()."""
        path = Path(store.store("requests", "old.whl", b"data"))
        stale = time.time() - store.ttl_seconds - 60
        os.utime(path, (stale, stale))
        assert store.evict_expired() == 1
        assert not store.contains("requests", "old.whl")

    def test_evict_expired_keeps_fresh_entries(self, store):
        """Entries within TTL survive evict_expired()."""
        store.store("requests", "fresh.whl", b"data")
        assert store.evict_expired() == 0
        assert store.contains("requests", "fresh.whl")

    def test_get_after_ttl_expiry_returns_none(self, store):
        """An expired artifact is no longer served by get()."""
        path = Path(store.store("requests", "old.whl", b"data"))
        stale = time.time() - store.ttl_seconds - 60
        os.utime(path, (stale, stale))
        store.evict_expired()
        assert store.get("requests", "old.whl") is None


class TestSafeRelativeTraversalGuard:
    """_safe_relative rejects absolute paths and '..' traversal."""

    def test_accepts_plain_names(self, store):
        """Well-formed package/filename pairs pass through unchanged."""
        rel = ArtifactStore._safe_relative("requests", "requests-2.32.0-py3-none-any.whl")
        assert rel == Path("requests") / "requests-2.32.0-py3-none-any.whl"

    def test_rejects_absolute_package(self, store):
        """An absolute package path cannot escape the store root."""
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("/etc", "x.whl")

    def test_rejects_absolute_filename(self, store):
        """An absolute filename cannot escape the store root."""
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("pkg", "/etc/passwd")

    def test_rejects_parent_traversal_in_package(self, store):
        """'..' segments in the package name are rejected."""
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("..", "x.whl")
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("../pkg", "x.whl")

    def test_rejects_parent_traversal_in_filename(self, store):
        """'..' segments in the filename are rejected."""
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("pkg", "../x.whl")
        with pytest.raises(ValueError):
            ArtifactStore._safe_relative("pkg", "a/../../x.whl")
