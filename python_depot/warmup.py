"""Cache warm-up service and CLI.

``WarmupService`` prefetches top-N packages (or an explicit list)
through the :class:`python_depot.pep503_cache.PyPICacheService` so that
a cold proxy has the most popular packages cached before first use.
Failures are recorded, never raised — a partially successful warm-up
still returns a useful ``WarmupResult``.

``TOP_PACKAGES`` is the seed corpus for ``prefetch_top``: the most
depended-upon packages on PyPI (mirrors the top of the uv ecosystem
hub's dependency graph).  Pass a richer corpus via ``top_packages`` when
constructing the service, or call ``prefetch(packages=[...])`` directly.
"""

from __future__ import annotations

import argparse
import asyncio
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
        return await self.prefetch(self.top_packages[:top_n])

    async def prefetch(self, packages: list[str]) -> WarmupResult:
        """Prefetch the given packages; failures are recorded, not raised."""
        cached = 0
        failed: list[str] = []
        for name in packages:
            try:
                await self.cache.get_simple_index(name)
                cached += 1
            except Exception:
                failed.append(name)
        return WarmupResult(requested=len(packages), cached=cached, failed=failed)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns process exit code."""
    parser = argparse.ArgumentParser(prog="python-depot-cache-warmup")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="number of top packages to prefetch (default: 10)",
    )
    args = parser.parse_args(argv)
    asyncio.run(WarmupService().prefetch_top(args.top))
    return 0
