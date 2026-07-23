# PythonDepot
Curated Python package discovery platform.

## Features

### 📦 Catalog
- Package discovery and management
- Search and filter packages
- Package metadata management
- Detailed package information

### ⭐ Ratings
- User ratings and reviews
- Average rating calculation
- Rating distribution
- Rating submission

### 🔍 Health Monitoring
- Package dependency health checks
- Vulnerability scanning
- Version compatibility monitoring
- Health status endpoints

### 📊 Analytics
- Trending packages tracking
- Popularity metrics
- Usage analytics
- Performance dashboards

### 📋 Reports
- Package analytics reports
- Health scan reports
- Usage statistics reports
- Custom report generation

## Badges

[![Tests Status](https://img.shields.io/badge/tests-14%2F14-brightgreen.svg)](./tests)
[![Lint Status](https://img.shields.io/badge/ruff-clean-brightgreen.svg)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL or SQLite database

### Installation Steps

```bash
# Clone the repository
cgit clone https://github.com/csaszarzoltan/python-depot.git
cd python-depot

# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn src.app:app --reload
```

### Database Setup

For SQLite (default):
```bash
# The application uses SQLite by default
# No additional setup required
```

For PostgreSQL:
```bash
# Update database configuration in src/database.py
# Configure DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:password@localhost/dbname"
```

## Getting Started

### First Steps

1. **Start the application**
   ```bash
   uvicorn src.app:app --reload
   ```

2. **Test the health endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Explore the API**
   - Visit `http://localhost:8000/docs` for interactive API documentation
   - Visit `http://localhost:8000/redoc` for ReDoc documentation

### Basic Usage Examples

#### 1. List all packages
```bash
curl http://localhost:8000/api/v1/packages/
```

#### 2. Get package details
```bash
curl http://localhost:8000/api/v1/packages/requests
```

#### 3. Submit a rating
```bash
curl -X POST http://localhost:8000/api/v1/ratings/requests \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "review": "Great package!"}'
```

## API Overview

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with API info |
| GET | `/health` | Health check endpoint |
| GET | `/api/v1/packages/` | List all packages |
| GET | `/api/v1/packages/{name}` | Get package by name |
| POST | `/api/v1/packages/` | Create new package |
| PUT | `/api/v1/packages/{name}` | Update package |
| DELETE | `/api/v1/packages/{name}` | Delete package |
| GET | `/api/v1/ratings/{name}` | Get ratings for package |
| POST | `/api/v1/ratings/{name}` | Submit rating |
| GET | `/api/v1/ratings/{name}/summary` | Get rating summary |
| GET | `/api/v1/reviews/{name}` | List reviews |
| POST | `/api/v1/reviews/{name}` | Submit review |
| GET | `/api/v1/reviews/{name}/{review_id}` | Get specific review |
| GET | `/api/v1/vulnerabilities/{name}` | List vulnerability scans |
| POST | `/api/v1/vulnerabilities/{name}/scan` | Trigger scan |
| GET | `/api/v1/vulnerabilities/{name}/latest` | Get latest scan |
| GET | `/api/v1/analytics/trending` | Get trending packages |
| GET | `/api/v1/analytics/popular` | Get popular packages |
| POST | `/api/v1/analytics/events` | Track analytics event |
| GET | `/api/v1/analytics/stats/{name}` | Get package stats |

### Rate Limiting

The API currently does not enforce rate limiting. For production use, consider adding rate limiting middleware.

## Deployment

### Railway

This project includes `railway.toml` for one-click deployment on [Railway](https://railway.app).

#### Deployment Steps

1. **Click "Deploy to Railway"**
   ```bash
   # Navigate to https://railway.app
   # Click "Deploy to Railway" button
   # Select your GitHub repository
   ```

2. **Environment Variables**

Set the following environment variables in Railway dashboard:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `postgresql://user:password@localhost/dbname` |
| `PYTHONPATH` | Python path (usually auto-set) | `src` |

3. **Database Setup**

Railway provides PostgreSQL databases. Configure your app to use the DATABASE_URL environment variable.

4. **Health Check**

The application includes a health check endpoint at `/health`. Railway uses this for health monitoring.

5. **Verify Deployment**

```bash
# After deployment, test the health endpoint
curl https://your-app.railway.app/health
```

### Docker / Procfile

The `Procfile` is compatible with Heroku, Render, and similar platforms.

### Local Development with Railway

To run locally with Railway configuration:

```bash
# Install Railway CLI
pip install railway

# Link existing project
railway link

# Deploy to Railway
railway up

# View logs
railway logs
```

## Development

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run tests with coverage
pytest -v --tb=short

# Run tests with coverage report
pytest --cov=src --cov-report=html
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test module
pytest tests/test_packages.py -v

# Run tests with asyncio mode
pytest tests/ --asyncio-mode=auto
```

### API Testing

```bash
# Test individual endpoints with curl

# Test health endpoint
curl http://localhost:8000/health

# Test package listing
curl http://localhost:8000/api/v1/packages/

# Test error handling
curl http://localhost:8000/api/v1/packages/nonexistent
```

## License

MIT

---

*PythonDepot is a curated Python package discovery platform designed to help developers find and manage Python packages effectively.*