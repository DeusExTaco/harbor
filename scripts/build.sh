#!/bin/bash
# Harbor Container Updater - Local Multi-Architecture Build Script
# This script builds Harbor for multiple architectures locally

set -e

# Configuration
IMAGE_NAME="harbor/harbor"
VERSION=${1:-"dev"}
PLATFORMS="linux/amd64,linux/arm64,linux/arm/v7"
DOCKERFILE="deploy/docker/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the project root
if [[ ! -f "pyproject.toml" ]]; then
    log_error "Please run this script from the Harbor project root directory"
    exit 1
fi

# Check if Docker buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    log_error "Docker buildx is required for multi-architecture builds"
    log_info "Install with: docker buildx install"
    exit 1
fi

log_info "Starting Harbor multi-architecture build"
log_info "Image: ${IMAGE_NAME}:${VERSION}"
log_info "Platforms: ${PLATFORMS}"
log_info "Dockerfile: ${DOCKERFILE}"

# Create/use buildx builder
BUILDER_NAME="harbor-builder"
if ! docker buildx inspect $BUILDER_NAME > /dev/null 2>&1; then
    log_info "Creating buildx builder: $BUILDER_NAME"
    docker buildx create --name $BUILDER_NAME --driver docker-container --bootstrap
fi

log_info "Using buildx builder: $BUILDER_NAME"
docker buildx use $BUILDER_NAME

# Build for multiple architectures
log_info "Building Harbor for multiple architectures..."
docker buildx build \
    --platform $PLATFORMS \
    --target production \
    --tag "${IMAGE_NAME}:${VERSION}" \
    --tag "${IMAGE_NAME}:latest" \
    --file $DOCKERFILE \
    --build-arg BUILDPLATFORM=linux/amd64 \
    --build-arg TARGETPLATFORM=linux/amd64 \
    --load \
    .

log_success "Multi-architecture build completed!"

# Test the built image
log_info "Testing the built image..."
docker run --rm "${IMAGE_NAME}:${VERSION}" python -c "
import app
print('✅ Harbor imports successfully')
print('✅ Build version: ${VERSION}')
"

log_success "Image test passed!"

# Show image information
log_info "Image information:"
docker images "${IMAGE_NAME}:${VERSION}"

log_success "Build completed successfully!"
log_info "To run Harbor: docker run -d -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock:ro ${IMAGE_NAME}:${VERSION}"
