# PythonDepot v0.7 Handoff

The primary implementation report is `docs/v0.7-product-engineering-report.md`.
The original broad product analysis is `docs/initial-product-analysis-and-requirements.md`.

## Quick validation

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest -q tests/test_product_ui_v07.py tests/test_product_ui.py tests/test_product_capabilities.py
uv run ruff check python_depot/product_ui.py python_depot/routers/product_pages.py tests/test_product_ui_v07.py
uv run uvicorn python_depot.api:app --reload
```

Open `/workspace/risk-inbox`, `/workspace/upgrade`, and `/workspace/decisions` to review the v0.7 workflow improvements.

## v0.8 continuation

See `docs/v0.8-continuation-report.md`. Risk operations now include atomic bulk triage, owner and due-date persistence, individual editing, and complete activity timelines.

## v0.9 continuation

See `docs/v0.9-continuation-report.md`. A persistent Projects workspace now stores repository context and immutable dependency snapshots, with added/removed/changed package delta reporting.


## v0.10 continuation

See `docs/v0.10-continuation-report.md`. Saved project context can now launch upgrade planning, package comparison, and project-filtered risk triage without repeated dependency entry.
