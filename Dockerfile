# Dockerfile for Railway deployment (DOCKERFILE builder)
# Pattern source: shared/patterns/railway-deploy-config.md
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (no dev dependencies in production)
RUN uv sync --frozen --no-dev 2>/dev/null || pip install --no-cache-dir -e .

# Copy application code
COPY python_depot/ python_depot/
COPY src/ src/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "python_depot.api:app", "--host", "0.0.0.0", "--port", "8000"]
