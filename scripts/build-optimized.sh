#!/bin/bash
# scripts/build-optimized.sh
# Build Harbor with all optimizations

export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Build with inline cache
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --cache-from harbor/harbor:latest \
  --tag harbor/harbor:latest \
  --tag harbor/harbor:$(git rev-parse --short HEAD) \
  -f deploy/docker/Dockerfile \
  .

# Check final size
docker images harbor/harbor:latest --format "Image size: {{.Size}}"

# Extract SBOM from image
docker run --rm harbor/harbor:latest cat /app/sbom.json > sbom-extracted.json
echo "SBOM extracted to sbom-extracted.json"
