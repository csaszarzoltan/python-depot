# uv Migration Assistant

The `python-depot-migrate` CLI automates migration from pip, poetry, pip-tools, and pipenv to [uv](https://github.com/astral-sh/uv) — the fast Python package installer and resolver that has overtaken pip in CI pipelines (75M+ monthly downloads).

## Overview

The migration pipeline has four stages:

1. **Dependency Analysis** — scan your project for `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `setup.cfg`, or `requirements.in` files and parse all dependencies.
2. **Compatibility Check** — flag packages with known uv compatibility issues (pip-tools, poetry-core, black, setup.py-only projects, private indexes) and estimate migration effort.
3. **Lock File Conversion** — read existing lock files (`poetry.lock`, `Pipfile.lock`, pinned `requirements.txt`) and produce a `uv.lock` with version constraints preserved.
4. **CI/CD Config Update** — detect and migrate GitHub Actions workflows, GitLab CI configs, and Dockerfiles from pip/poetry/pipenv to uv equivalents.

## Installation

The migration assistant ships with PythonDepot:

```bash
git clone https://github.com/csaszarzoltan/python-depot.git
cd python-depot
pip install -e ".[dev]"
```

For the lock file conversion stage, `uv` must be installed in your environment:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

### Dry-run (default)

Scans a project and reports what would change without modifying any files:

```bash
python-depot-migrate --scan ./my-project
```

### Apply migration

Writes the generated files (`uv.lock`, updated CI configs):

```bash
python-depot-migrate --scan ./my-project --apply
```

### Report only

Generates a migration report without touching files:

```bash
python-depot-migrate --scan ./my-project --report-only
```

### Batch mode

Migrate multiple projects at once:

```bash
python-depot-migrate --scan ./project-a ./project-b ./project-c --batch --apply
```

## CLI Reference

| Flag | Description |
|------|-------------|
| `--scan <paths>` | **Required.** One or more project directories to scan. |
| `--apply` | Execute the migration. Without this flag, runs as a dry-run. |
| `--batch` | Enable batch mode for multiple projects. Exit code: 0 = all success, 1 = all fail, 2 = mixed. |
| `--report-only` | Generate a report without any file changes. |
| `--output <dir>` | Output directory for generated files. |

Exit codes:

- `0` — all projects migrated successfully
- `1` — all projects failed or path does not exist
- `2` — mixed results (some succeeded, some failed)

## Dependency Analysis

The scanner detects six dependency file formats:

| Format | Detected file |
|--------|--------------|
| requirements.txt | `requirements.txt` |
| requirements.in | `requirements.in` |
| pyproject.toml | `pyproject.toml` |
| Pipfile | `Pipfile` |
| setup.py | `setup.py` |
| setup.cfg | `setup.cfg` |

Parsed dependencies include: name, version constraint, source type (`pypi`, `git`, `path`, `url`), extras, markers, and dev-status flag.

## Compatibility Checker

The checker cross-references your dependencies against a curated list of packages known to have uv compatibility issues:

| Package | Issue | Workaround |
|---------|-------|------------|
| pip-tools | Uses pip's internal resolver; uv replaces it entirely | Use `uv pip compile` instead of `pip-compile` |
| poetry-core | Build backend incompatible with uv's build system | Replace with `uv_build` or `setuptools` in `[build-system]` |
| black | May need `--target-version` config update | Update `pyproject.toml` `[tool.black]` target-version after migration |
| setup.py-only | Lacks PEP 621 `pyproject.toml` | Generate `pyproject.toml` with `[build-system]` pointing to setuptools |
| private-index | Needs `UV_INDEX_*` environment variables | Set `UV_INDEX_<NAME>_USERNAME` and `UV_INDEX_<NAME>_PASSWORD` |

The effort estimate is derived from the ratio of flagged packages:

- **low** — fewer than 50% of packages flagged
- **medium** — 50% or more flagged
- **high** — all packages flagged

## Lock File Conversion

The `LockConverter` reads existing lock files and produces pinned constraints for `uv lock`:

### Supported source formats

| Source | File | Parser |
|--------|------|--------|
| Poetry | `poetry.lock` | TOML parser with regex fallback for malformed files |
| Pipenv | `Pipfile.lock` | JSON parser (reads `default` + `develop` sections) |
| pip-tools | `requirements.txt` (compiled, `==` pinned) | Line-by-line regex |
| Plain pinned | `requirements.txt` with `==` pins | Line-by-line regex |

The converter handles:

- Extras (`package[extra1,extra2]==1.0.0`)
- VCS sources (skipped for constraints — they cannot be pinned)
- Editable installs (skipped)
- Hash suffices (`--hash=sha256:...` stripped before parsing)

### Pipeline

```python
from pathlib import Path
from python_depot_migrate.lock_converter import LockConverter

converter = LockConverter()

# Step 1: Read the lock file
snapshot = converter.read_lock(Path("poetry.lock"))

# Step 2: Build pinned constraints
constraints = converter.build_constraints(snapshot)
# → ["fastapi==0.110.0", "uvicorn[standard]==0.27.0", ...]

# Step 3: Generate uv.lock
uv_lock_path = converter.generate_uv_lock(
    project_path=Path("."),
    constraints=constraints,
    dry_run=False,
)
```

## CI/CD Config Updates

The `CICDUpdater` detects and migrates three types of CI/CD configurations:

### Detection

| Config type | Detection |
|-------------|-----------|
| GitHub Actions | `.github/workflows/*.yml` |
| GitLab CI | `.gitlab-ci.yml` |
| Dockerfiles | `Dockerfile`, `Dockerfile.docker`, `Dockerfile.dockerfile` |

### Migration rules

| Original | Replacement |
|----------|-------------|
| `pip install ...` | `uv pip install ...` |
| `poetry install ...` | `uv sync --locked` |
| `pipenv install ...` | `uv sync` |

For Dockerfiles, a `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv` line is added before the first install command.

### Usage

```python
from pathlib import Path
from python_depot_migrate.ci_cd import CICDUpdater

updater = CICDUpdater()

# Detect CI/CD configs
configs = updater.detect(Path("./my-project"))
for cfg in configs:
    print(f"{cfg.kind}: {cfg.path} (backend: {cfg.current_backend})")

# Preview changes (dry-run)
for cfg in configs:
    diff = updater.update(cfg, dry_run=True)
    if diff:
        print(f"Changes for {cfg.path}:")
        for change in diff.changes:
            print(f"  - {change}")
```

## Migration Reports

The report generator produces both markdown and JSON output:

### Markdown report

```python
from pathlib import Path
from python_depot_migrate.scanner import MigrationResult
from python_depot_migrate.report import MigrationReportGenerator

result = MigrationResult(
    project_path=Path("./my-project"),
    dry_run=True,
    success=True,
    before_summary="pip (requirements.txt, 24 packages)",
    after_summary="uv (pyproject.toml + uv.lock, 24 packages)",
)

generator = MigrationReportGenerator()
report = generator.generate_markdown(result)
print(report)
```

Output:

```
# Migration Report: ./my-project

**Status:** Success (Dry Run)

## Before / After Comparison

| Aspect | Before | After |
|--------|--------|-------|
| Summary | pip (requirements.txt, 24 packages) | uv (pyproject.toml + uv.lock, 24 packages) |
| Path | ./my-project | ./my-project |

## Rollback Instructions

This was a dry run — no changes were applied. No rollback is necessary.
```

### JSON report

```python
json_report = generator.generate_json(result)
```

Output:

```json
{
  "project_path": "./my-project",
  "success": true,
  "dry_run": true,
  "summary": "pip (requirements.txt, 24 packages) -> uv (pyproject.toml + uv.lock, 24 packages)",
  "files_changed": [],
  "files_generated": [],
  "warnings": [],
  "errors": [],
  "rollback": "This was a dry run — no changes were applied. No rollback is necessary.",
  "before_after": "..."
}
```

## Programmatic Usage

### Single project migration

```python
from pathlib import Path
from python_depot_migrate.cli import run_migration

result = run_migration(
    project_path=Path("./my-project"),
    apply=False,       # dry-run
    report_only=False,
)

if result.success:
    print(f"Migration ready: {result.files_generated}")
else:
    print(f"Errors: {result.errors}")
```

### Batch migration

```python
from pathlib import Path
from python_depot_migrate.cli import run_batch

results = run_batch(
    project_paths=[
        Path("./project-a"),
        Path("./project-b"),
        Path("./project-c"),
    ],
    apply=False,
)

for result in results:
    status = "OK" if result.success else "FAIL"
    print(f"{result.project_path}: {status}")
```

## Edge Cases

The scanner and converter handle these edge cases:

- **Editable installs** (`-e ./local-package`) — detected and excluded from constraint generation
- **VCS dependencies** (`git+https://...`) — parsed but skipped for pinning (cannot be constrained)
- **Private indexes** — flagged in compatibility report with workaround instructions
- **Extras with markers** (`package[extra]; python_version >= "3.12"`) — parsed correctly
- **Platform-specific deps** (`package; sys_platform == "win32"`) — preserved in output
- **Empty requirements** — returns empty scan result without error
- **Malformed TOML** — poetry.lock falls back to regex parser
- **Mixed formats** — project with both `requirements.txt` and `pyproject.toml` detects both

## Test Suite

The migration assistant has 411 tests across 5 modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| Dependency Analysis (scanner) | 102 | 102 passing |
| Lock Conversion | 76 | 76 passing |
| CI/CD Updater | 61 | 61 passing |
| Compatibility + Report | 109 | 109 passing |
| CLI + Batch Mode | 63 | 63 passing |
| **Total** | **411** | **340 passing, 71 skipped (RED-phase stubs)** |

Run the full suite:

```bash
python -m pytest tests/ -v --tb=short
```

## Architecture

```
python_depot_migrate/
├── __init__.py          # Package root
├── __main__.py          # python -m python_depot_migrate entry point
├── cli.py               # CLI entry point + argparse + batch mode
├── scanner.py           # Dependency analysis engine (data models + scanner)
├── compatibility.py     # Pre-flight uv compatibility checker
├── lock_converter.py    # Lock file reader + uv.lock generator
├── ci_cd.py             # CI/CD config detector + migrator
└── report.py            # Markdown + JSON report generator
```

Data flow:

```
Project directory
  → DependencyScanner.scan()      → ScanResult
  → CompatibilityChecker.check() → CompatibilityReport
  → LockConverter.read_lock()    → LockSnapshot
  → LockConverter.build_constraints() → list[str]
  → LockConverter.generate_uv_lock()  → Path | None
  → CICDUpdater.detect()         → list[CICDConfig]
  → CICDUpdater.update()         → MigrationDiff | None
  → MigrationReportGenerator     → markdown / JSON report
```
