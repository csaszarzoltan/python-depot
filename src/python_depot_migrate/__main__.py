"""Allow running as: python -m python_depot_migrate."""
from __future__ import annotations

import sys

from python_depot_migrate.cli import main

if __name__ == "__main__":
    sys.exit(main())
