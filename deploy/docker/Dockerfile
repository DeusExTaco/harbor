# Harbor Container Updater - Enhanced Multi-Architecture Production Dockerfile
# Supports: linux/amd64, linux/arm64, linux/arm/v7
# Optimized for home lab deployments across all platforms

# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.13
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# =============================================================================
# Base Stage - Platform Detection and Common Setup
# =============================================================================
FROM --platform=$BUILDPLATFORM python:${PYTHON_VERSION}-slim AS base

# Build arguments for platform optimization
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG HARBOR_VERSION
ARG BUILD_MODE=production
ARG GIT_SHA
ARG BUILD_TIMESTAMP

# Display build information
RUN echo "🏗️ Harbor Multi-Architecture Build" && \
    echo "Target Platform: ${TARGETPLATFORM}" && \
    echo "Build Platform: ${BUILDPLATFORM}" && \
    echo "Harbor Version: ${HARBOR_VERSION}" && \
    echo "Build Mode: ${BUILD_MODE}" && \
    echo ""

# Platform-aware system dependencies installation
RUN apt-get update && \
    if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 Installing minimal dependencies for ARMv7 (Raspberry Pi 3)..."; \
        apt-get install -y --no-install-recommends \
            curl \
            ca-certificates \
            tzdata; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "🍎 Installing balanced dependencies for ARM64..."; \
        apt-get install -y --no-install-recommends \
            curl \
            ca-certificates \
            tzdata \
            gcc \
            libc6-dev; \
    else \
        echo "🖥️ Installing full dependencies for AMD64..."; \
        apt-get install -y --no-install-recommends \
            curl \
            ca-certificates \
            tzdata \
            gcc \
            g++ \
            libc6-dev; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Create harbor user
RUN groupadd -r harbor && useradd -r -g harbor harbor

# Python environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# Build Stage - Dependencies and Compilation
# =============================================================================
FROM base AS builder

# Platform-specific build dependencies
RUN if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7: Installing minimal build tools..."; \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            libffi-dev \
            && rm -rf /var/lib/apt/lists/*; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "🍎 ARM64: Installing balanced build tools..."; \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            git \
            libffi-dev \
            libssl-dev \
            && rm -rf /var/lib/apt/lists/*; \
    else \
        echo "🖥️ AMD64: Installing full build tools..."; \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            git \
            libffi-dev \
            libssl-dev \
            pkg-config \
            && rm -rf /var/lib/apt/lists/*; \
    fi

# Set up build environment
WORKDIR /app

# Copy dependency files
COPY requirements/ ./requirements/
COPY pyproject.toml ./

# Platform-specific Python dependency installation with optimizations
RUN echo "🔧 Installing Python dependencies for ${TARGETPLATFORM}..." && \
    pip install --upgrade pip setuptools wheel && \
    if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7 optimizations: Using pre-compiled wheels and minimal dependencies"; \
        pip install --user --no-warn-script-location \
            --prefer-binary \
            --only-binary=:all: \
            --timeout 1800 \
            -r requirements/base.txt \
            -r requirements/production.txt || \
        pip install --user --no-warn-script-location \
            --timeout 1800 \
            --no-build-isolation \
            -r requirements/base.txt \
            -r requirements/production.txt; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "🍎 ARM64 optimizations: Balanced build approach with wheel preference"; \
        pip install --user --no-warn-script-location \
            --prefer-binary \
            --timeout 900 \
            -r requirements/base.txt \
            -r requirements/production.txt; \
    else \
        echo "🖥️ AMD64: Standard build approach with full optimization"; \
        pip install --user --no-warn-script-location \
            --timeout 600 \
            -r requirements/base.txt \
            -r requirements/production.txt; \
    fi && \
    echo "✅ Dependencies installed successfully for ${TARGETPLATFORM}"

# =============================================================================
# Production Stage - Final Image
# =============================================================================
FROM base AS production

# Copy Python packages from builder
COPY --from=builder /root/.local /home/harbor/.local

# Set up application directory
WORKDIR /app
COPY --chown=harbor:harbor . .

# Create required directories
RUN mkdir -p /app/data /app/logs /app/config /app/backups && \
    chown -R harbor:harbor /app

# Platform-specific optimizations and environment setup
RUN echo "🔧 Applying platform-specific optimizations for ${TARGETPLATFORM}..." && \
    if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7 (Raspberry Pi 3) optimizations:"; \
        echo 'HARBOR_MAX_WORKERS=1' >> /app/.env.platform; \
        echo 'MAX_CONCURRENT_UPDATES=1' >> /app/.env.platform; \
        echo 'DATABASE_POOL_SIZE=2' >> /app/.env.platform; \
        echo 'LOG_RETENTION_DAYS=7' >> /app/.env.platform; \
        echo 'REGISTRY_CACHE_TTL=7200' >> /app/.env.platform; \
        echo 'ENABLE_METRICS=false' >> /app/.env.platform; \
        echo 'PYTHONOPTIMIZE=1' >> /app/.env.platform; \
        echo 'MALLOC_TRIM_THRESHOLD_=100000' >> /app/.env.platform; \
        echo 'REGISTRY_TIMEOUT=60' >> /app/.env.platform; \
        echo 'REGISTRY_RETRY_COUNT=5' >> /app/.env.platform; \
        echo 'PULL_TIMEOUT_SECONDS=1800' >> /app/.env.platform; \
        echo 'UPDATE_TIMEOUT_SECONDS=900' >> /app/.env.platform; \
        echo 'CLEANUP_KEEP_IMAGES=1' >> /app/.env.platform; \
        echo "   - Single worker process for memory efficiency"; \
        echo "   - Sequential container updates only"; \
        echo "   - Minimal database connection pool (2)"; \
        echo "   - Short log retention (7 days)"; \
        echo "   - Extended cache TTL (2 hours)"; \
        echo "   - Metrics disabled to save resources"; \
        echo "   - Python optimizations enabled"; \
        echo "   - Aggressive memory trimming"; \
        echo "   - Extended timeouts for slower operations"; \
        echo "   - Minimal image retention"; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "🍎 ARM64 (Apple Silicon, Pi 4, Modern ARM) optimizations:"; \
        echo 'HARBOR_MAX_WORKERS=2' >> /app/.env.platform; \
        echo 'MAX_CONCURRENT_UPDATES=1' >> /app/.env.platform; \
        echo 'DATABASE_POOL_SIZE=5' >> /app/.env.platform; \
        echo 'LOG_RETENTION_DAYS=14' >> /app/.env.platform; \
        echo 'REGISTRY_CACHE_TTL=3600' >> /app/.env.platform; \
        echo 'ENABLE_METRICS=true' >> /app/.env.platform; \
        echo 'REGISTRY_TIMEOUT=45' >> /app/.env.platform; \
        echo 'PULL_TIMEOUT_SECONDS=900' >> /app/.env.platform; \
        echo 'UPDATE_TIMEOUT_SECONDS=600' >> /app/.env.platform; \
        echo 'CLEANUP_KEEP_IMAGES=2' >> /app/.env.platform; \
        echo "   - Dual worker processes for balanced performance"; \
        echo "   - Sequential updates for safety"; \
        echo "   - Standard database pool (5 connections)"; \
        echo "   - Moderate log retention (14 days)"; \
        echo "   - Standard cache TTL (1 hour)"; \
        echo "   - All features enabled including metrics"; \
        echo "   - Moderate timeouts for good performance"; \
        echo "   - Standard image retention"; \
    else \
        echo "🖥️ AMD64 (Intel/AMD) optimizations:"; \
        echo 'HARBOR_MAX_WORKERS=auto' >> /app/.env.platform; \
        echo 'MAX_CONCURRENT_UPDATES=5' >> /app/.env.platform; \
        echo 'DATABASE_POOL_SIZE=10' >> /app/.env.platform; \
        echo 'LOG_RETENTION_DAYS=30' >> /app/.env.platform; \
        echo 'REGISTRY_CACHE_TTL=1800' >> /app/.env.platform; \
        echo 'ENABLE_METRICS=true' >> /app/.env.platform; \
        echo 'REGISTRY_TIMEOUT=30' >> /app/.env.platform; \
        echo 'PULL_TIMEOUT_SECONDS=600' >> /app/.env.platform; \
        echo 'UPDATE_TIMEOUT_SECONDS=300' >> /app/.env.platform; \
        echo 'CLEANUP_KEEP_IMAGES=3' >> /app/.env.platform; \
        echo "   - Auto-scaled workers based on CPU cores"; \
        echo "   - Concurrent updates for maximum efficiency"; \
        echo "   - Large database pool (10 connections)"; \
        echo "   - Extended log retention (30 days)"; \
        echo "   - Optimized cache TTL (30 minutes)"; \
        echo "   - All features enabled with full performance"; \
        echo "   - Fast timeouts for responsive operation"; \
        echo "   - Extended image retention for rollback"; \
    fi && \
    echo "✅ Platform optimizations applied for ${TARGETPLATFORM}"

# Create platform detection script
RUN cat > /app/scripts/detect_platform.py << 'PLATFORM_DETECT_EOF'
#!/usr/bin/env python3
"""Platform detection and optimization for Harbor Container Updater."""

import os
import platform


def detect_platform_optimizations():
    """Detect platform and return optimization settings."""
    arch = platform.machine().lower()
    target_platform = os.getenv('HARBOR_TARGET_PLATFORM', '')

    print(f"🔍 Platform Detection:")
    print(f"   Architecture: {arch}")
    print(f"   Platform: {platform.platform()}")
    print(f"   Target Platform: {target_platform}")

    # Platform-specific recommendations
    if arch in ['x86_64', 'amd64'] or 'amd64' in target_platform:
        print(f"🖥️  AMD64 Detected - Full Performance Configuration")
        print(f"   - Workers: auto-scaled")
        print(f"   - Concurrent Updates: 5")
        print(f"   - Database Pool: 10")
        print(f"   - Features: All enabled")
    elif arch in ['aarch64', 'arm64'] or 'arm64' in target_platform:
        print(f"🍎  ARM64 Detected - Balanced Configuration")
        print(f"   - Workers: 2")
        print(f"   - Concurrent Updates: 1")
        print(f"   - Database Pool: 5")
        print(f"   - Features: All enabled")
    elif arch.startswith('arm') or 'arm/v7' in target_platform:
        print(f"🥧  ARMv7 Detected - Memory Optimized Configuration")
        print(f"   - Workers: 1")
        print(f"   - Concurrent Updates: 1")
        print(f"   - Database Pool: 2")
        print(f"   - Features: Metrics disabled")
    else:
        print(f"❓  Unknown Platform - Using AMD64 defaults")


if __name__ == "__main__":
    detect_platform_optimizations()
PLATFORM_DETECT_EOF

# Make platform detection script executable
RUN chmod +x /app/scripts/detect_platform.py

# Switch to non-root user
USER harbor

# Add local packages to PATH
ENV PATH="/home/harbor/.local/bin:$PATH"

# Enhanced application metadata with platform info
LABEL org.opencontainers.image.title="Harbor Container Updater"
LABEL org.opencontainers.image.description="Automated Docker container updates for home labs and enterprises"
LABEL org.opencontainers.image.source="https://github.com/DeusExTaco/harbor"
LABEL org.opencontainers.image.documentation="https://harbor-docs.dev"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="Harbor Team"
LABEL org.opencontainers.image.version="${HARBOR_VERSION}"
LABEL harbor.milestone="M0"
LABEL harbor.build-mode="${BUILD_MODE}"
LABEL harbor.git-sha="${GIT_SHA}"
LABEL harbor.build-timestamp="${BUILD_TIMESTAMP}"
LABEL harbor.target-platform="${TARGETPLATFORM}"
LABEL harbor.supports-arm="true"
LABEL harbor.raspberry-pi-ready="true"
LABEL harbor.apple-silicon-ready="true"
LABEL harbor.multi-arch="true"

# Platform-specific environment defaults
ENV HARBOR_MODE=homelab \
    LOG_LEVEL=INFO \
    ENABLE_AUTO_DISCOVERY=true \
    HARBOR_TARGET_PLATFORM=${TARGETPLATFORM}

# Expose application port
EXPOSE 8080

# Platform-aware health check with appropriate timeouts
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Enhanced platform-optimized startup command
CMD ["sh", "-c", "echo '🏗️ Harbor Container Updater Starting...'; echo 'Platform: $HARBOR_TARGET_PLATFORM'; python /app/scripts/detect_platform.py; set -a; [ -f /app/.env.platform ] && . /app/.env.platform; echo 'Workers: ${HARBOR_MAX_WORKERS:-auto}'; echo 'Starting Harbor...'; exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080 --workers ${HARBOR_MAX_WORKERS:-1}"]

# =============================================================================
# Development Stage - Enhanced for Multi-Platform Development
# =============================================================================
FROM builder AS development

# Install development dependencies with platform awareness
COPY requirements/development.txt ./
RUN echo "🔧 Installing development dependencies for ${TARGETPLATFORM}..." && \
    if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7: Installing minimal development tools"; \
        pip install --user --no-warn-script-location \
            --prefer-binary \
            --timeout 1800 \
            pytest pytest-asyncio pytest-cov \
            ruff mypy \
            httpx; \
    else \
        echo "📦 Installing full development dependencies"; \
        pip install --user --no-warn-script-location \
            --timeout 900 \
            -r requirements/development.txt; \
    fi

# Copy application code
WORKDIR /app
COPY --chown=harbor:harbor . .

# Create directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R harbor:harbor /app

# Development tools (platform-conditional)
RUN if [ "$TARGETPLATFORM" != "linux/arm/v7" ]; then \
        apt-get update && apt-get install -y \
            --no-install-recommends \
            vim \
            htop \
            && rm -rf /var/lib/apt/lists/*; \
    fi

USER harbor
ENV PATH="/home/harbor/.local/bin:$PATH"

# Development-specific environment
ENV HARBOR_MODE=development \
    LOG_LEVEL=DEBUG \
    ENABLE_AUTO_DISCOVERY=true \
    HARBOR_RELOAD=true

# Platform-specific development optimizations
RUN if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7 development mode: Ultra-minimal resource usage"; \
        echo 'HARBOR_MAX_WORKERS=1' >> /app/.env.dev; \
        echo 'DATABASE_POOL_SIZE=1' >> /app/.env.dev; \
        echo 'LOG_RETENTION_DAYS=3' >> /app/.env.dev; \
        echo 'ENABLE_METRICS=false' >> /app/.env.dev; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "🍎 ARM64 development mode: Balanced resources"; \
        echo 'HARBOR_MAX_WORKERS=2' >> /app/.env.dev; \
        echo 'DATABASE_POOL_SIZE=3' >> /app/.env.dev; \
        echo 'LOG_RETENTION_DAYS=7' >> /app/.env.dev; \
        echo 'ENABLE_METRICS=true' >> /app/.env.dev; \
    else \
        echo "🖥️ AMD64 development mode: Full resources"; \
        echo 'HARBOR_MAX_WORKERS=auto' >> /app/.env.dev; \
        echo 'DATABASE_POOL_SIZE=5' >> /app/.env.dev; \
        echo 'LOG_RETENTION_DAYS=14' >> /app/.env.dev; \
        echo 'ENABLE_METRICS=true' >> /app/.env.dev; \
    fi

# Development health check with platform-appropriate timeout
HEALTHCHECK --interval=60s --timeout=20s --start-period=180s --retries=2 \
    CMD python scripts/health_check.py || exit 1

# Development command with auto-reload and platform awareness
CMD ["sh", "-c", "echo '🔧 Harbor Development Mode Starting...'; echo 'Platform: $HARBOR_TARGET_PLATFORM'; python /app/scripts/detect_platform.py; set -a; [ -f /app/.env.dev ] && . /app/.env.dev; echo 'Development Workers: ${HARBOR_MAX_WORKERS:-1}'; exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080 --reload --workers 1"]

# =============================================================================
# Testing Stage - For CI/CD Pipeline Testing
# =============================================================================
FROM development AS testing

# Install additional testing dependencies
RUN echo "🧪 Installing testing dependencies for ${TARGETPLATFORM}..." && \
    if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        echo "🥧 ARMv7: Minimal testing setup"; \
        pip install --user --no-warn-script-location \
            --prefer-binary \
            pytest-xdist; \
    else \
        echo "📦 Full testing setup"; \
        pip install --user --no-warn-script-location \
            playwright \
            pytest-xdist \
            pytest-benchmark; \
    fi

# Copy test files
COPY tests/ ./tests/

# Platform-aware test configuration
ENV PYTEST_OPTS="" \
    HARBOR_MODE=development

# Test runner script
RUN cat > /app/scripts/run_tests.py << 'TEST_RUNNER_EOF'
#!/usr/bin/env python3
"""Platform-aware test runner for Harbor."""

import os
import platform
import subprocess
import sys


def get_platform_test_config():
    """Get platform-specific test configuration."""
    arch = platform.machine().lower()
    target_platform = os.getenv('HARBOR_TARGET_PLATFORM', '')

    if arch.startswith('arm') or 'arm/v7' in target_platform:
        return {
            'workers': 1,
            'timeout': 300,
            'maxfail': 3,
            'verbosity': '-v',
            'markers': '-m "not slow"'  # Skip slow tests on ARMv7
        }
    elif 'arm64' in arch or 'arm64' in target_platform:
        return {
            'workers': 2,
            'timeout': 180,
            'maxfail': 5,
            'verbosity': '-v',
            'markers': ''
        }
    else:
        return {
            'workers': 'auto',
            'timeout': 120,
            'maxfail': 10,
            'verbosity': '-v',
            'markers': ''
        }


def main():
    """Run tests with platform-specific configuration."""
    config = get_platform_test_config()

    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        f'--workers={config["workers"]}',
        f'--timeout={config["timeout"]}',
        f'--maxfail={config["maxfail"]}',
        config['verbosity'],
        '--tb=short'
    ]

    if config['markers']:
        cmd.append(config['markers'])

    print(f"🧪 Running tests on {platform.machine()} with config: {config}")

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
TEST_RUNNER_EOF

RUN chmod +x /app/scripts/run_tests.py

# Test command
CMD ["python", "/app/scripts/run_tests.py"]