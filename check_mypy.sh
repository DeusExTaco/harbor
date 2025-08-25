#!/bin/bash
# Harbor Container Updater - MyPy Check Script
# Test mypy configuration fixes

set -e

echo "🔍 Running MyPy Type Check"
echo "=========================="
echo ""

# Check if mypy is available
if ! command -v mypy &> /dev/null; then
    echo "❌ mypy not found"
    echo "💡 Install with: pip install mypy"
    exit 1
fi

# Run mypy on the app directory
echo "📁 Checking app/ directory..."
mypy app/

echo ""
echo "📁 Checking configuration files..."
mypy app/config.py

echo ""
echo "📁 Checking main application..."
mypy app/main.py

echo ""
echo "✅ MyPy type checking completed successfully!"
echo ""
echo "📊 Results:"
echo "   - No type errors found"
echo "   - Configuration module passes type checking"
echo "   - Main application module passes type checking"
echo ""
echo "🎯 Next steps:"
echo "   1. Run full pre-commit: pre-commit run --all-files"
echo "   2. Test configuration: python test_config.py"
echo "   3. Test application: python app/main.py"
