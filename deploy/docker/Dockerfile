# syntax=docker/dockerfile:1.7
# Harbor Container Updater - Production Dockerfile
# Supports multi-architecture builds: amd64, arm64

ARG PYTHON_VERSION=3.13
ARG TARGETPLATFORM
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# Base stage with common dependencies
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user for security
RUN groupadd -r harbor && useradd -r -g harbor harbor

# Python environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# =============================================================================
# Build stage for compiling dependencies
# =============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements/base.txt requirements/production.txt ./requirements/
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --user --no-warn-script-location \
        -r requirements/base.txt \
        -r requirements/production.txt

# =============================================================================
# Production runtime stage
# =============================================================================
FROM base AS production

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/harbor/.local

# Set up application directory
WORKDIR /app

# Copy application code
COPY --chown=harbor:harbor app/ ./app/
COPY --chown=harbor:harbor scripts/ ./scripts/
COPY --chown=harbor:harbor pyproject.toml README.md LICENSE ./

# Create required directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/config /app/backups && \
    chown -R harbor:harbor /app

# Platform-specific optimizations for ARM
ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "Applying ARM64 optimizations" && \
        echo 'HARBOR_MAX_WORKERS=2' >> /app/.env.arm && \
        echo 'MAX_CONCURRENT_UPDATES=1' >> /app/.env.arm && \
        echo 'DATABASE_POOL_SIZE=3' >> /app/.env.arm; \
    fi

# Switch to non-root user
USER harbor

# Add local Python packages to PATH
ENV PATH="/home/harbor/.local/bin:$PATH"

# Application metadata
LABEL org.opencontainers.image.title="Harbor Container Updater" \
      org.opencontainers.image.description="Automated Docker container updates for home labs and enterprises" \
      org.opencontainers.image.source="https://github.com/DeusExTaco/harbor" \
      org.opencontainers.image.documentation="https://harbor-docs.dev" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Harbor Team" \
      org.opencontainers.image.version="0.1.0"

# Expose application port
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Set default environment for production
ENV HARBOR_MODE=homelab \
    LOG_LEVEL=INFO \
    ENABLE_AUTO_DISCOVERY=true

# Default command
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

# =============================================================================
# Development stage
# =============================================================================
FROM builder AS development

# Install development dependencies
COPY requirements/development.txt ./requirements/
RUN pip install --user --no-warn-script-location \
    -r requirements/development.txt

# Copy application code with development setup
WORKDIR /app
COPY --chown=harbor:harbor . .

# Create development directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R harbor:harbor /app

# Install development tools
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER harbor

# Add development Python packages to PATH
ENV PATH="/home/harbor/.local/bin:$PATH"

# Development environment variables
ENV HARBOR_MODE=development \
    LOG_LEVEL=DEBUG \
    DEV_RELOAD=true

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--reload"]
