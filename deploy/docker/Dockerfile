# Harbor Container Updater - Simplified Production Dockerfile
# This approach focuses on getting it working first, optimization later

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Create harbor user
RUN groupadd -r harbor && useradd -r -g harbor harbor

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first (Docker layer caching)
COPY requirements/ ./requirements/

# Install Python dependencies as root (simpler)
RUN pip install --upgrade pip && \
    echo "📦 Installing Harbor dependencies..." && \
    pip install -r requirements/base.txt && \
    pip install -r requirements/production.txt && \
    echo "✅ Dependencies installed successfully" && \
    echo "🔍 Verifying uvicorn installation..." && \
    python -c "import uvicorn; print(f'✅ uvicorn {uvicorn.__version__} ready')" && \
    python -c "import fastapi; print(f'✅ fastapi {fastapi.__version__} ready')"

# Copy application code
COPY --chown=harbor:harbor app/ ./app/
COPY --chown=harbor:harbor scripts/ ./scripts/
COPY --chown=harbor:harbor pyproject.toml README.md LICENSE ./

# Create data directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R harbor:harbor /app

# Switch to harbor user
USER harbor

# Final verification - simplified to avoid Docker parsing issues
RUN echo "🔍 Final check as harbor user..." && \
    python -c "import sys; print('✅ Python executable:', sys.executable)" && \
    python -c "import uvicorn; print('✅ uvicorn available')" && \
    python -c "import fastapi; print('✅ fastapi available')" && \
    python -c "import sqlalchemy; print('✅ sqlalchemy available')" && \
    python -c "import sys; sys.path.insert(0, '/app'); import app; print(f'✅ Harbor app v{app.__version__} ready')" && \
    echo "✅ Container is ready to start!"

# Set default environment
ENV HARBOR_MODE=homelab \
    LOG_LEVEL=INFO \
    ENABLE_AUTO_DISCOVERY=true

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Start command - keep it simple
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
