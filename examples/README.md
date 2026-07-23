# PythonDepot Examples

This directory contains runnable Python example scripts that demonstrate the PythonDepot API.

## Prerequisites

```bash
# From the project root
cd python-depot
pip install -e ".[dev]"

# Start the development server
uvicorn python_depot.api:app --reload
```

## Examples

| # | Script | Covers |
|---|--------|--------|
| 1 | `basic_operations.py` | Package CRUD (list, create, update, delete) |
| 2 | `catalog_api.py` | Catalog API with search and filtering |
| 3 | `health_checks.py` | Health endpoint, vulnerability scanning |
| 4 | `search_and_trends.py` | Package search with pagination, time-series trends |
| 5 | `reviews_and_ratings.py` | Ratings, reviews, and rating summaries |

## Usage

While the server is running, execute any example from a separate terminal:

```bash
cd python-depot/examples

python basic_operations.py
python catalog_api.py
python health_checks.py
python search_and_trends.py
python reviews_and_ratings.py
```

Each example:
- Connects to `http://localhost:8000` by default
- Prints detailed output of each API operation
- Does NOT require a running database — endpoints return placeholder data

## Customization

Change the `base_url` in any example to target a different server:

```python
base_url = "https://your-app.railway.app"
```

## Dependencies

- `httpx` (installed via `pip install -e ".[dev]"`)
- A running PythonDepot server
