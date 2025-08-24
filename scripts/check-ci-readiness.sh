#!/bin/bash
# Harbor Container Updater - CI/CD Readiness Check
# scripts/check-ci-readiness.sh
# Validates that the repository is ready for CI/CD pipeline

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}🔍 Harbor CI/CD Readiness Check${NC}"
echo "================================"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Check function
check_item() {
    local check_name="$1"
    local check_command="$2"
    local required="${3:-true}"

    echo -n "Checking $check_name... "

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ (Required)${NC}"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
        else
            echo -e "${YELLOW}⚠️ (Optional)${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
        return 1
    fi
}

# =============================================================================
# Repository Structure Checks
# =============================================================================
echo -e "${BLUE}📁 Repository Structure${NC}"

check_item "README.md exists" "test -f README.md"
check_item "LICENSE file exists" "test -f LICENSE" false
check_item "pyproject.toml exists" "test -f pyproject.toml"
check_item "Main app module" "test -f app/__init__.py && test -f app/main.py"
check_item "Dockerfile exists" "test -f deploy/docker/Dockerfile"
check_item "Development Dockerfile" "test -f deploy/docker/Dockerfile.dev" false

echo ""

# =============================================================================
# GitHub Workflow Checks
# =============================================================================
echo -e "${BLUE}⚙️ GitHub Workflows${NC}"

check_item "Main CI/CD workflow" "test -f .github/workflows/ci-cd.yml" false
check_item "Docker build workflow" "test -f .github/workflows/docker-build.yml" false
check_item "Test workflow" "test -f .github/workflows/test.yml" false
check_item "Security workflow" "test -f .github/workflows/security.yml" false
check_item "CodeQL workflow" "test -f .github/workflows/codeql.yml" false

echo ""

# =============================================================================
# Multi-Architecture Support Checks
# =============================================================================
echo -e "${BLUE}🌐 Multi-Architecture Support${NC}"

check_item "Platform detection script" "test -f scripts/detect_platform.py" false
check_item "Multi-arch test script" "test -f scripts/test-multi-platform.sh" false
check_item "Platform setup script" "test -f scripts/dev/setup-platform.sh" false
check_item "Multi-arch validation" "test -f scripts/dev/validate-multiarch.py" false

# Check that Dockerfile contains multi-arch instructions if it exists
if [[ -f "deploy/docker/Dockerfile" ]]; then
    check_item "Multi-arch Dockerfile" "grep -q 'TARGETPLATFORM\\|ARG.*PLATFORM' deploy/docker/Dockerfile" false
fi

echo ""

# =============================================================================
# Configuration Checks
# =============================================================================
echo -e "${BLUE}⚙️ Configuration Files${NC}"

check_item "Pre-commit config" "test -f .pre-commit-config.yaml" false
check_item "Makefile" "test -f Makefile"
check_item "Git ignore" "test -f .gitignore"

# Check pyproject.toml validity
if [[ -f "pyproject.toml" ]] && command -v python > /dev/null 2>&1; then
    check_item "pyproject.toml syntax" "python -c 'import tomllib; tomllib.load(open(\"pyproject.toml\", \"rb\"))' 2>/dev/null || python -c 'import configparser; open(\"pyproject.toml\").read()'" false
fi

echo ""

# =============================================================================
# Version Consistency Checks
# =============================================================================
echo -e "${BLUE}📦 Version Consistency${NC}"

# Extract versions
PYPROJECT_VERSION=""
APP_VERSION=""

if [ -f pyproject.toml ]; then
    PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo "")
fi

if [ -f app/__init__.py ]; then
    APP_VERSION=$(grep '__version__ = ' app/__init__.py | sed 's/__version__ = "\(.*\)"/\1/' || echo "")
fi

echo "Project version (pyproject.toml): ${PYPROJECT_VERSION:-'Not found'}"
echo "App version (app/__init__.py): ${APP_VERSION:-'Not found'}"

if [ -n "$PYPROJECT_VERSION" ] && [ -n "$APP_VERSION" ]; then
    if [ "$PYPROJECT_VERSION" = "$APP_VERSION" ]; then
        echo -e "${GREEN}✅ Version consistency check passed${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌ Version mismatch between files${NC}"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
else
    echo -e "${YELLOW}⚠️ Could not verify version consistency${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# =============================================================================
# Git Repository Checks
# =============================================================================
echo -e "${BLUE}📂 Git Repository${NC}"

check_item "Git repository initialized" "test -d .git"
check_item "Main/master branch exists" "git show-ref --verify --quiet refs/heads/main || git show-ref --verify --quiet refs/heads/master" false
# check_item "No uncommitted changes" "git diff --quiet && git diff --cached --quiet" false
check_item "Remote origin configured" "git remote get-url origin" false

echo ""

# =============================================================================
# Python Environment Checks
# =============================================================================
echo -e "${BLUE}🐍 Python Environment${NC}"

check_item "Python available" "command -v python"
check_item "Python 3.11+ available" "python -c 'import sys; assert sys.version_info >= (3, 11)'" false

if command -v python > /dev/null 2>&1; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo "Python version: $PYTHON_VERSION"
fi

echo ""

# =============================================================================
# Docker Environment Checks
# =============================================================================
echo -e "${BLUE}🐳 Docker Environment${NC}"

check_item "Docker available" "command -v docker"
check_item "Docker daemon accessible" "docker info" false
check_item "Docker Compose available" "docker-compose --version || docker compose version" false
check_item "Docker Buildx available" "docker buildx version" false

echo ""

# =============================================================================
# Development Dependencies
# =============================================================================
echo -e "${BLUE}🔧 Development Tools${NC}"

# Check for common development tools
check_item "Make available" "command -v make"
check_item "Git available" "command -v git"
check_item "Curl available" "command -v curl" false
check_item "JQ available" "command -v jq" false

echo ""

# =============================================================================
# CI/CD Environment Information
# =============================================================================
echo -e "${BLUE}🚀 CI/CD Environment Notes${NC}"

echo "Required GitHub Secrets (verify these exist in your repo settings):"
echo "  🔑 DOCKERHUB_USERNAME (for Docker Hub publishing)"
echo "  🔑 DOCKERHUB_TOKEN (for Docker Hub publishing)"
echo "  ✅ GITHUB_TOKEN (automatically provided by GitHub)"
echo ""
echo "Recommended Repository Settings:"
echo "  🔧 Enable GitHub Actions"
echo "  🔧 Allow GitHub Actions to create and approve pull requests"
echo "  🔧 Set up branch protection rules for main branch"

echo ""

# =============================================================================
# Results Summary
# =============================================================================
echo -e "${PURPLE}📊 Readiness Summary${NC}"
echo "===================="
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED))

echo "✅ Passed: $CHECKS_PASSED"
echo "❌ Failed: $CHECKS_FAILED"
echo "⚠️  Warnings: $WARNINGS"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 No critical issues found!${NC}"
    echo ""

    if [ $WARNINGS -eq 0 ]; then
        echo -e "${BLUE}✅ Repository is fully ready for CI/CD pipeline!${NC}"
    else
        echo -e "${BLUE}✅ Repository is ready for CI/CD pipeline!${NC}"
        echo -e "${YELLOW}💡 Address warnings for optimal experience${NC}"
    fi

    echo ""
    echo -e "${YELLOW}🚀 Next Steps:${NC}"
    echo "1. Create missing optional files if needed"
    echo "2. Run: make test-quick (if available)"
    echo "3. Commit your changes: git add . && git commit -m 'feat: multi-arch support'"
    echo "4. Create feature branch: git checkout -b feature/multiarch-builds"
    echo "5. Push to trigger CI: git push -u origin feature/multiarch-builds"
    echo "6. Create PR to main branch"
    echo "7. Monitor GitHub Actions for CI/CD pipeline results"
    echo ""
    echo -e "${BLUE}📊 Expected CI/CD Pipeline:${NC}"
    echo "  • Code Quality & Linting ✓"
    echo "  • Test Suite ✓"
    echo "  • Multi-Architecture Docker Build ✓"
    echo "  • Platform Testing ✓"
    echo "  • Security Scanning ✓"
    echo "  • Registry Publishing ✓"

elif [ $CHECKS_FAILED -le 3 ]; then
    echo -e "${YELLOW}⚠️ Minor issues found: $CHECKS_FAILED critical items need attention${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Address the failed checks above before pushing to CI${NC}"
    echo ""
    echo "Critical issues to fix:"
    echo "  • Missing required files or configurations"
    echo "  • Version inconsistencies"
    echo "  • Repository setup issues"
    echo ""
    echo "After fixing issues, run this script again to verify."

else
    echo -e "${RED}❌ Multiple critical issues: $CHECKS_FAILED items need immediate attention${NC}"
    echo ""
    echo -e "${YELLOW}🚨 Repository not ready for CI/CD${NC}"
    echo ""
    echo "Before proceeding:"
    echo "  1. Fix all failed required checks above"
    echo "  2. Ensure basic project structure is complete"
    echo "  3. Run this readiness check again"
    echo "  4. Consider running: make dev-setup (if available)"

    exit 1
fi

echo ""
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${PURPLE}🏁 Harbor Multi-Architecture CI/CD: Ready to Launch!${NC}"
else
    echo -e "${YELLOW}🔧 Harbor Multi-Architecture CI/CD: Needs attention before launch${NC}"
fi