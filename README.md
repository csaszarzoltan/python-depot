# PythonDepot

Curated Python package discovery platform.

## Features

- Package discovery and management
- User ratings and reviews
- Vulnerability scanning
- Analytics and trending packages

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn src.app:app --reload

# Run tests
pytest -v

# Lint
ruff check .
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/packages/` | List packages |
| GET | `/api/v1/packages/{name}` | Get package details |
| GET | `/api/v1/ratings/{name}` | Get package ratings |
| GET | `/api/v1/reviews/{name}` | Get package reviews |
| GET | `/api/v1/vulnerabilities/{name}` | Get vulnerability scans |
| GET | `/api/v1/analytics/trending` | Trending packages |

## Deployment

### Railway

This project includes `railway.toml` for one-click deployment on [Railway](https://railway.app).

### Docker / Procfile

The `Procfile` is compatible with Heroku, Render, and similar platforms.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run tests with coverage
pytest -v --tb=short
```

## License

MIT
