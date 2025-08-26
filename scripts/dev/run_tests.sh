#!/bin/bash
# run_tests.sh - Harbor Test Suite Runner
# Comprehensive test execution script for Harbor M0 Database implementation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    print_error "Please run this script from the Harbor project root directory"
    exit 1
fi

print_header "Harbor M0 Database Implementation Test Suite"
print_info "Testing all components before proceeding to next milestone"

# Set test environment
export TESTING=true
export HARBOR_MODE=development
export LOG_LEVEL=DEBUG

# Create test results directory
mkdir -p test_results

# Function to run a test section
run_test_section() {
    local section_name="$1"
    local test_command="$2"
    local log_file="test_results/${section_name,,}.log"

    print_info "Running: $section_name"

    if eval "$test_command" > "$log_file" 2>&1; then
        print_success "$section_name"
        return 0
    else
        print_error "$section_name - Check $log_file for details"
        return 1
    fi
}

# Test 1: Database Implementation Test Script
print_header "1. Database Implementation Comprehensive Test"
if python test_db_implementation.py --verbose; then
    print_success "Database implementation test passed"
    db_test_passed=true
else
    print_error "Database implementation test failed"
    db_test_passed=false
fi

# Test 2: Basic Application Startup
print_header "2. Application Startup Test"
print_info "Testing basic application creation and health endpoints"

if python -c "
import asyncio
import sys
sys.path.insert(0, '.')

async def test_app():
    try:
        from app.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        print(f'✅ Root endpoint: {data[\"name\"]} v{data[\"version\"]}')

        # Test health endpoint
        response = client.get('/healthz')
        assert response.status_code == 200
        health = response.json()
        print(f'✅ Health check: {health[\"status\"]}')

        # Test database endpoints if available
        response = client.get('/database/status')
        if response.status_code == 200:
            db_status = response.json()
            print(f'✅ Database status: {db_status[\"status\"]}')
        else:
            print('⚠️  Database endpoints not available')

        print('✅ Application startup test completed successfully')
        return True

    except Exception as e:
        print(f'❌ Application startup test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_app())
exit(0 if result else 1)
"; then
    print_success "Application startup test"
    app_test_passed=true
else
    print_error "Application startup test failed"
    app_test_passed=false
fi

# Test 3: Check if pytest is working with our configuration
print_header "3. Pytest Configuration Test"
if python -m pytest --version > /dev/null 2>&1; then
    print_success "Pytest is available"

    # Test our conftest.py
    if python -c "
import sys
sys.path.insert(0, 'tests')
try:
    import conftest
    print('✅ Test configuration loaded successfully')
    print('✅ Available fixtures:')

    # Get fixture names
    import inspect
    fixtures = []
    for name in dir(conftest):
        obj = getattr(conftest, name)
        if hasattr(obj, '_pytestfixturefunction'):
            fixtures.append(name)

    for fixture in sorted(fixtures)[:10]:  # Show first 10 fixtures
        print(f'  - {fixture}')

    if len(fixtures) > 10:
        print(f'  ... and {len(fixtures) - 10} more fixtures')

    print(f'✅ Total fixtures available: {len(fixtures)}')

except Exception as e:
    print(f'❌ Test configuration error: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"; then
        print_success "Pytest configuration"
        pytest_config_passed=true
    else
        print_error "Pytest configuration failed"
        pytest_config_passed=false
    fi
else
    print_warning "Pytest not available - skipping pytest tests"
    pytest_config_passed=false
fi

# Test 4: Import all our modules to check for syntax errors
print_header "4. Module Import Test"
modules_to_test=(
    "app.config"
    "app.db.base"
    "app.db.config"
    "app.db.models.user"
    "app.db.models.api_key"
    "app.db.models.settings"
    "app.db.models.container"
    "app.db.models.policy"
    "app.db.repositories.base"
    "app.db.repositories.user"
    "app.db.repositories.container"
    "app.db.session"
    "app.db.init"
    "app.main"
)

import_test_passed=true
for module in "${modules_to_test[@]}"; do
    if python -c "import $module; print('✅ $module')" 2>/dev/null; then
        continue
    else
        print_error "Failed to import $module"
        python -c "import $module" || true  # Show the actual error
        import_test_passed=false
    fi
done

if $import_test_passed; then
    print_success "All modules imported successfully"
else
    print_error "Some module imports failed"
fi

# Test 5: Check database models can be created
print_header "5. Database Models Creation Test"
if python -c "
import sys
sys.path.insert(0, '.')

try:
    from app.db.models.user import User
    from app.db.models.api_key import APIKey
    from app.db.models.settings import SystemSettings
    from app.db.models.container import Container
    from app.db.models.policy import ContainerPolicy
    from app.db.base import Base
    import uuid

    print('✅ All database models imported')

    # Test model creation (without database)
    user = User(username='test', password_hash='hash')
    print(f'✅ User model created: {user}')

    settings = SystemSettings(id=1)
    print(f'✅ SystemSettings model created: {settings}')

    container_uid = str(uuid.uuid4())
    container = Container(
        uid=container_uid,
        docker_name='test',
        image_repo='nginx',
        image_tag='latest',
        image_ref='nginx:latest',
        status='running'
    )
    print(f'✅ Container model created: {container}')

    policy = ContainerPolicy(container_uid=container_uid)
    print(f'✅ ContainerPolicy model created: {policy}')

    print('✅ All database models can be instantiated')

except Exception as e:
    print(f'❌ Database models test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"; then
    print_success "Database models creation test"
    models_test_passed=true
else
    print_error "Database models creation test failed"
    models_test_passed=false
fi

# Test 6: Security Middleware Test
print_header "6. Security Middleware Test"
if python -c "
import sys
sys.path.insert(0, '.')

try:
    from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
    from app.middleware.input_sanitizer import InputSanitizerMiddleware

    print('✅ Security middleware modules imported')

    # Test middleware creation
    SecurityHeadersMiddleware
    RateLimitMiddleware
    InputSanitizerMiddleware

    print('✅ All security middleware classes available')

except Exception as e:
    print(f'❌ Security middleware test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"; then
    print_success "Security middleware test"
    security_test_passed=true
else
    print_error "Security middleware test failed"
    security_test_passed=false
fi

# Summary
print_header "Test Results Summary"

tests_results=(
    "Database Implementation:$db_test_passed"
    "Application Startup:$app_test_passed"
    "Pytest Configuration:$pytest_config_passed"
    "Module Imports:$import_test_passed"
    "Database Models:$models_test_passed"
    "Security Middleware:$security_test_passed"
)

passed_tests=0
total_tests=${#tests_results[@]}

for result in "${tests_results[@]}"; do
    test_name="${result%:*}"
    test_passed="${result#*:}"

    if [ "$test_passed" = "true" ]; then
        print_success "$test_name"
        ((passed_tests++))
    else
        print_error "$test_name"
    fi
done

echo ""
print_info "Overall Result: $passed_tests/$total_tests tests passed"

if [ $passed_tests -eq $total_tests ]; then
    print_header "🎉 ALL TESTS PASSED!"
    print_success "M0 Database implementation is ready for next milestone"
    print_info "You can proceed with:"
    print_info "  - M0 Authentication System (next immediate task)"
    print_info "  - M1 Container Discovery (next milestone)"
    echo ""
    print_info "To run individual components:"
    print_info "  python test_db_implementation.py --verbose"
    print_info "  uvicorn app.main:create_app --factory --reload"
    print_info "  python -m pytest tests/unit/db/ -v --database"
    exit 0
else
    print_header "💥 SOME TESTS FAILED"
    print_error "Please review the errors above before proceeding"
    print_info "Check test_results/ directory for detailed logs"
    exit 1
fi
