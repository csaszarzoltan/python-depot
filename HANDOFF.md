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
