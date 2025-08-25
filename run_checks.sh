#!/bin/bash
# Harbor Container Updater - Code Quality Checks
# Run all code quality checks before commit

set -e

echo "🛳️ Harbor Code Quality Checks"
echo "=============================="
echo ""

# Function to run a check and report results
run_check() {
    local name="$1"
    local cmd="$2"

    echo "🔍 Running $name..."
    if eval "$cmd"; then
        echo "✅ $name passed"
    else
        echo "❌ $name failed"
        return 1
    fi
    echo ""
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Please run from the Harbor project root directory"
    exit 1
fi

# Install dependencies if needed
if [[ "${1:-}" == "--install" ]]; then
    echo "📦 Installing development dependencies..."
    pip install -r requirements/development.txt
    echo ""
fi

# Run Ruff linting and formatting
run_check "Ruff Linting" "ruff check --fix ."
run_check "Ruff Formatting" "ruff format --check ."

# Run Black formatting check
run_check "Black Formatting" "black --check ."

# Run MyPy type checking
run_check "MyPy Type Checking" "mypy app/"

# Run configuration tests
run_check "Configuration Tests" "python test_config.py"

# Run configuration validation
run_check "Configuration Validation" "python scripts/validate_config.py"

# Test application startup
run_check "Application Startup Test" "python app/main.py > /dev/null 2>&1"

echo "🎉 All checks passed!"
echo ""
echo "✅ Code quality:"
echo "   - Linting: Passed"
echo "   - Formatting: Passed"
echo "   - Type checking: Passed"
echo ""
echo "✅ Configuration:"
echo "   - Tests: Passed"
echo "   - Validation: Passed"
echo ""
echo "✅ Application:"
echo "   - Startup: Passed"
echo ""
echo "🚀 Ready for commit and push!"
echo ""
echo "💡 Next steps:"
echo "   1. Run tests: pytest (when tests are implemented)"
echo "   2. Run pre-commit: pre-commit run --all-files"
echo "   3. Build Docker image: docker build -t harbor:test ."
echo "   4. Test container: docker run --rm harbor:test"
