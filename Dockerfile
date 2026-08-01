# Production image for PythonDepot v0.7
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy package metadata and installable sources before dependency resolution.
COPY pyproject.toml README.md ./
COPY python_depot/ python_depot/
COPY python_depot_migrate/ python_depot_migrate/
COPY src/ src/

RUN uv pip install --system --no-cache .

RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn python_depot.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
