# deploy/docker/Dockerfile
# syntax=docker/dockerfile:1
# Harbor Container Updater - Fully Optimized Production Build

FROM python:3.13-slim-bullseye AS builder

# Build-time optimizations
ARG PIP_NO_CACHE_DIR=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_COMPILE=1
ARG PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements/ requirements/

# Build wheels without compilation for smaller size
# Using --no-cache-dir explicitly for hadolint
RUN pip wheel --no-cache-dir --wheel-dir=/wheels --no-compile \
    -r requirements/base.txt \
    -r requirements/production.txt

# Generate SBOM in builder stage
RUN pip install --no-cache-dir pip-licenses && \
    pip-licenses --format=json --with-urls --with-licenses > /build/sbom.json && \
    pip-licenses --format=markdown > /build/sbom.md && \
    pip uninstall -y pip-licenses

# Final stage - Fully optimized
FROM python:3.13-slim-bullseye

# Metadata and security labels
LABEL org.opencontainers.image.title="Harbor Container Updater" \
      org.opencontainers.image.description="Automated Docker container updates" \
      org.opencontainers.image.source="https://github.com/DeusExTaco/harbor" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Harbor Team" \
      security.scan="trivy" \
      security.contact="security@harbor.dev" \
      security.sbom="/app/sbom.json"

# Create non-root user
RUN groupadd -r harbor --gid=1000 && \
    useradd -r -g harbor --uid=1000 --home-dir=/app --create-home --shell=/usr/sbin/nologin harbor

# Install minimal runtime dependencies with security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    /usr/share/doc/* /usr/share/man/* /usr/share/info/* \
    /usr/share/lintian/* /usr/share/linda/*

# Install Python packages with optimization
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-compile --no-index \
    --find-links=/wheels /wheels/* && \
    rm -rf /wheels /root/.cache /tmp/* && \
    # Aggressive Python cleanup
    find /usr/local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local -type d -name 'test' -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local -type f -name '*.pyc' -delete && \
    find /usr/local -type f -name '*.pyo' -delete && \
    find /usr/local -type f -name '*.a' -delete && \
    find /usr/local -type f -name '*.la' -delete && \
    rm -rf /usr/local/lib/python*/dist-packages/*.dist-info && \
    rm -rf /usr/local/lib/python*/site-packages/*.dist-info/RECORD && \
    rm -rf /usr/local/lib/python*/site-packages/*.dist-info/WHEEL && \
    rm -rf /usr/local/lib/python*/site-packages/*.dist-info/REQUESTED

WORKDIR /app

# Copy application files with minimal footprint
COPY --chown=1000:1000 app/ ./app/
COPY --chown=1000:1000 scripts/ ./scripts/
COPY --chown=1000:1000 LICENSE README.md ./

# Copy SBOM and security policy
COPY --from=builder --chown=1000:1000 /build/sbom.json /build/sbom.md ./

# Copy security policy (create this file in your repo)
COPY --chown=1000:1000 security.json ./

# Validate security policy
RUN python -c "import json; json.load(open('/app/security.json'))" && \
    # Set up directories with strict permissions
    mkdir -p /app/data /app/logs && \
    chown -R 1000:1000 /app && \
    chmod -R u=rwX,go=rX /app && \
    chmod 755 /app/scripts/*.py && \
    # Remove write permissions from code files
    find /app -type f -name "*.py" -exec chmod 444 {} \;

# Switch to non-root user
USER 1000:1000

# Security-hardened environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    HARBOR_MODE=homelab \
    LOG_LEVEL=INFO

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "scripts/health_check.py"]

ENTRYPOINT ["python", "-m", "app.main"]
