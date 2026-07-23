# Changelog

All notable changes to PythonDepot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-07-22

### Added
- FastAPI application with app factory pattern
- SQLAlchemy models: Package, Rating, Review, VulnerabilityScan, AnalyticsEvent
- API routers: packages, ratings, reviews, vulnerabilities, analytics
- Health check endpoint at `/health`
- SQLite database configuration
- GitHub Actions CI (Python 3.10, 3.11, 3.12)
- Railway deployment config (nixpacks)
- Procfile for Heroku-style deployments
- Ruff linting configuration
- Test suite with pytest + httpx
