"""Cache warm-up service and CLI (pre-dev stub).

The ``WarmupResult`` dataclass and ``TOP_PACKAGES`` seed corpus are real so
interface tests pass immediately; ``WarmupService`` prefetch methods and
the ``main`` CLI entry point raise ``NotImplementedError`` until the
developer implements this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from python_depot.pep503_cache import PyPICacheService

__all__ = ["TOP_PACKAGES", "WarmupResult", "WarmupService", "main"]

TOP_PACKAGES: list[str] = ["requests", "numpy", "pandas"]


@dataclass
class WarmupResult:
    """Outcome of a warm-up run."""

    requested: int = 0
    cached: int = 0
    failed: list[str] = field(default_factory=list)


class WarmupService:
    """Prefetch top-N packages (or an explicit list) through the cache."""

    def __init__(
        self,
        cache: PyPICacheService | None = None,
        top_packages: list[str] | None = None,
    ) -> None:
        self.cache = cache or PyPICacheService()
        self.top_packages = list(top_packages or TOP_PACKAGES)

    async def prefetch_top(self, top_n: int = 10) -> WarmupResult:
        """Prefetch the first top_n packages from the seed corpus."""
        raise NotImplementedError

    async def prefetch(self, packages: list[str]) -> WarmupResult:
        """Prefetch the given packages; failures are recorded, not raised."""
        raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns process exit code."""
    raise NotImplementedError
