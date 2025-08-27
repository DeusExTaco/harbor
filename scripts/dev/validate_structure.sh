#!/bin/bash
# Validates project structure matches specification

REQUIRED_DIRS=(
    "app/api"
    "app/auth"
    "app/db/models"
    "app/db/repositories"
    "app/services"
    "app/runtimes"
    "tests/unit"
    "tests/integration"
    "deploy/docker"
    "config"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing: $dir"
    fi
done
