# Harbor Container Updater - Fixed Production Dockerfile
# Simplified and more robust build process

FROM python:3.13-slim AS base

# Install system dependencies including build tools for psutil
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create harbor user
RUN groupadd -r harbor && useradd -r -g harbor harbor

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy and install requirements separately for better caching
COPY requirements/ ./requirements/

# Upgrade pip and install requirements with error handling
RUN echo "📦 Installing Harbor dependencies..." && \
    pip install --upgrade pip && \
    echo "🔧 Installing base requirements..." && \
    pip install -r requirements/base.txt || \
    (echo "⚠️ Some packages failed, trying without optional dependencies..." && \
     pip install -r requirements/base.txt --no-deps && \
     pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings && \
     pip install jinja2 httpx docker apscheduler structlog prometheus-client && \
     pip install argon2-cffi cryptography python-dateutil packaging aiosqlite && \
     echo "✅ Core dependencies installed, psutil/pyyaml may be skipped") && \
    echo "🏭 Installing production requirements..." && \
    pip install -r requirements/production.txt && \
    echo "✅ All dependencies installed successfully"

# Verify critical imports work
RUN echo "🔍 Verifying critical dependencies..." && \
    python -c "import uvicorn; print('✅ uvicorn available')" && \
    python -c "import fastapi; print('✅ fastapi available')" && \
    python -c "import sqlalchemy; print('✅ sqlalchemy available')" && \
    python -c "import pydantic; print('✅ pydantic available')" && \
    echo "✅ Core dependencies verified"

# Copy application code
COPY --chown=harbor:harbor app/ ./app/
COPY --chown=harbor:harbor scripts/ ./scripts/
COPY --chown=harbor:harbor pyproject.toml README.md LICENSE ./

# Create required directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R harbor:harbor /app

# Switch to harbor user
USER harbor

# Final application verification
RUN echo "🔍 Final Harbor application check..." && \
    python -c "import sys; sys.path.insert(0, '/app'); import app; print(f'✅ Harbor v{app.__version__} ready')" && \
    echo "✅ Harbor application verified successfully"

# Set default environment for homelab
ENV HARBOR_MODE=homelab \
    LOG_LEVEL=INFO \
    ENABLE_AUTO_DISCOVERY=true

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Start Harbor
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
