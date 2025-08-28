#!/bin/bash
# scripts/dev/run_all_tests.sh
"""
Harbor Complete Test Suite Runner - Extended Version

Runs all tests including additional security and integration tests.
Stops on first failure for critical tests (1-7), then continues with extended tests.

Usage:
    ./run_all_tests.sh [--skip-server] [--quick]

Options:
    --skip-server  Skip server startup and API tests
    --quick        Run only essential tests (skip optional extended tests)
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
SKIP_SERVER=false
QUICK_MODE=false

for arg in "$@"; do
    case $arg in
        --skip-server)
            SKIP_SERVER=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            ;;
    esac
done

# Test results storage
declare -A test_results
declare -a test_order

# Server PID for cleanup
SERVER_PID=""

# Function to print headers
print_header() {
    echo ""
    echo "================================================================"
    echo " $1"
    echo "================================================================"
    echo ""
}

# Function to print test start
print_test_start() {
    echo -e "${BLUE}[TEST $1] Starting: $2${NC}"
    echo "----------------------------------------------------------------"
}

# Function to print test result
print_test_result() {
    local test_num=$1
    local test_name=$2
    local status=$3

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ [TEST $test_num] PASSED: $test_name${NC}"
        test_results["$test_num"]="PASS"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  [TEST $test_num] WARNING: $test_name${NC}"
        test_results["$test_num"]="WARN"
    else
        echo -e "${RED}❌ [TEST $test_num] FAILED: $test_name${NC}"
        test_results["$test_num"]="FAIL"
    fi
    test_order+=("$test_num")
    echo ""
}

# Function to print summary
print_summary() {
    print_header "TEST SUMMARY"

    local passed=0
    local warned=0
    local failed=0

    for test_num in "${test_order[@]}"; do
        local status="${test_results[$test_num]}"
        local test_name=""

        case $test_num in
            1) test_name="Configuration System Test";;
            2) test_name="Environment Check";;
            3) test_name="Security Middleware Test";;
            4) test_name="Database Implementation Test";;
            5) test_name="Authentication System Test";;
            6) test_name="API Key Manual Test";;
            7) test_name="Pre-commit Checks";;
            8) test_name="Server Start";;
            9) test_name="Login API Test";;
            10) test_name="API Key Creation Test";;
            11) test_name="API Key Authentication Test";;
            12) test_name="Docker Integration Test";;
            13) test_name="Registry Client Test";;
            14) test_name="Security Scan";;
            15) test_name="Import Cycle Detection";;
            16) test_name="Performance Baseline";;
        esac

        if [ "$status" = "PASS" ]; then
            echo -e "${GREEN}✅ Test $test_num: $test_name${NC}"
            ((passed++))
        elif [ "$status" = "WARN" ]; then
            echo -e "${YELLOW}⚠️  Test $test_num: $test_name${NC}"
            ((warned++))
        else
            echo -e "${RED}❌ Test $test_num: $test_name${NC}"
            ((failed++))
        fi
    done

    echo ""
    echo "Total: $passed passed, $warned warnings, $failed failed out of ${#test_order[@]} tests"

    if [ $failed -eq 0 ]; then
        if [ $warned -gt 0 ]; then
            echo -e "${YELLOW}⚠️  ALL TESTS PASSED WITH WARNINGS${NC}"
        else
            echo -e "${GREEN}🎉 ALL TESTS PASSED PERFECTLY!${NC}"
        fi
        return 0
    else
        echo -e "${RED}💥 SOME TESTS FAILED${NC}"
        return 1
    fi
}

# Function to cleanup server
cleanup_server() {
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi
}

# Trap to ensure server cleanup
trap cleanup_server EXIT

# Change to project root (assuming script is in scripts/dev)
cd "$(dirname "$0")/../.." || exit 1

print_header "HARBOR COMPLETE TEST SUITE (EXTENDED)"
echo "Starting comprehensive test suite..."
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Mode: $([ "$QUICK_MODE" = true ] && echo "QUICK" || echo "FULL")"
echo ""

# ============================================================================
# CORE TESTS (1-7) - Stop on failure
# ============================================================================

# Test 1: Configuration System
print_test_start 1 "Configuration System Test"
if python scripts/dev/test_config.py; then
    print_test_result 1 "Configuration System Test" "PASS"
else
    print_test_result 1 "Configuration System Test" "FAIL"
    print_summary
    exit 1
fi

# Test 2: Environment Check
print_test_start 2 "Environment Check"
if python scripts/dev/check_environment.py; then
    print_test_result 2 "Environment Check" "PASS"
else
    print_test_result 2 "Environment Check" "FAIL"
    print_summary
    exit 1
fi

# Test 3: Security Middleware
print_test_start 3 "Security Middleware Test"
if python scripts/dev/test_security_middleware.py; then
    print_test_result 3 "Security Middleware Test" "PASS"
else
    print_test_result 3 "Security Middleware Test" "FAIL"
    print_summary
    exit 1
fi

# Test 4: Database Implementation
print_test_start 4 "Database Implementation Test"
if python scripts/dev/test_db_implementation.py --verbose; then
    print_test_result 4 "Database Implementation Test" "PASS"
else
    print_test_result 4 "Database Implementation Test" "FAIL"
    print_summary
    exit 1
fi

# Test 5: Authentication System
print_test_start 5 "Authentication System Test"
if python scripts/dev/test_auth_system.py; then
    print_test_result 5 "Authentication System Test" "PASS"
else
    print_test_result 5 "Authentication System Test" "FAIL"
    print_summary
    exit 1
fi

# Test 6: API Key Manual Test
print_test_start 6 "API Key Manual Test"
if python scripts/dev/test_api_key_manual.py; then
    print_test_result 6 "API Key Manual Test" "PASS"
else
    print_test_result 6 "API Key Manual Test" "FAIL"
    print_summary
    exit 1
fi

# Test 7: Pre-commit Checks
print_test_start 7 "Pre-commit Checks"
if pre-commit run --all-files; then
    print_test_result 7 "Pre-commit Checks" "PASS"
else
    print_test_result 7 "Pre-commit Checks" "FAIL"
    print_summary
    exit 1
fi

# All core tests passed
echo ""
echo -e "${GREEN}✅ All core tests (1-7) passed!${NC}"

# ============================================================================
# EXTENDED TESTS (12-16) - Continue on failure
# ============================================================================

if [ "$QUICK_MODE" = false ]; then
    echo "Running extended test suite..."

    # Test 12: Docker Integration
    print_test_start 12 "Docker Integration Test"
    if python scripts/dev/test_docker_integration.py; then
        print_test_result 12 "Docker Integration Test" "PASS"
    else
        print_test_result 12 "Docker Integration Test" "WARN"
    fi

    # Test 13: Registry Client
    print_test_start 13 "Registry Client Test"
    if python scripts/dev/test_registry_client.py; then
        print_test_result 13 "Registry Client Test" "PASS"
    else
        print_test_result 13 "Registry Client Test" "WARN"
    fi

    # Test 14: Security Scan
    print_test_start 14 "Security Scan"
    if python scripts/dev/test_security_scan.py; then
        print_test_result 14 "Security Scan" "PASS"
    else
        print_test_result 14 "Security Scan" "WARN"
    fi

    # Test 15: Import Cycle Detection
    print_test_start 15 "Import Cycle Detection"
    if python scripts/dev/test_import_cycles.py; then
        print_test_result 15 "Import Cycle Detection" "PASS"
    else
        print_test_result 15 "Import Cycle Detection" "WARN"
    fi

    # Test 16: Performance Baseline
    print_test_start 16 "Performance Baseline"
    if python scripts/dev/test_performance_baseline.py; then
        print_test_result 16 "Performance Baseline" "PASS"
    else
        print_test_result 16 "Performance Baseline" "WARN"
    fi
else
    echo "Skipping extended tests (quick mode)..."
fi

# ============================================================================
# SERVER AND API TESTS (8-11)
# ============================================================================

if [ "$SKIP_SERVER" = false ]; then
    echo ""
    echo "Proceeding to server tests..."

    # Test 8: Start Server
    print_test_start 8 "Server Start"
    echo "Starting Harbor server..."

    # Create a temporary file for server output
    SERVER_LOG=$(mktemp /tmp/harbor_server.XXXXXX.log)

    # Start server in background
    python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080 --reload > "$SERVER_LOG" 2>&1 &
    SERVER_PID=$!

    echo "Server starting with PID: $SERVER_PID"
    echo "Waiting for server to be ready..."

    # Wait for server to be ready
    MAX_WAIT=30
    WAITED=0
    SERVER_READY=false

    while [ $WAITED -lt $MAX_WAIT ]; do
        if curl -s http://localhost:8080/healthz > /dev/null 2>&1; then
            SERVER_READY=true
            break
        fi
        sleep 1
        ((WAITED++))
        echo -n "."
    done
    echo ""

    if [ "$SERVER_READY" = true ]; then
        echo -e "${GREEN}Server started successfully!${NC}"
        print_test_result 8 "Server Start" "PASS"

        # Test 9: Login API Test
        print_test_start 9 "Login API Test"
        echo "Testing login endpoint..."

        LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
          -H "Content-Type: application/json" \
          -d '{"username": "admin", "password": "3CdCDURCtKQiArev"}' 2>&1) # pragma: allowlist secret

        echo "Response:"
        echo "$LOGIN_RESPONSE" | python -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"

        if echo "$LOGIN_RESPONSE" | grep -q '"success"'; then
            print_test_result 9 "Login API Test" "PASS"
            CSRF_TOKEN=$(echo "$LOGIN_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('csrf_token', ''))" 2>/dev/null)
        else
            print_test_result 9 "Login API Test" "WARN"
        fi

        # Test 10: API Key Creation Test
        print_test_start 10 "API Key Creation Test"
        echo "Testing API key creation..."

        if [ -z "$CSRF_TOKEN" ]; then
            echo "No CSRF token available, skipping test"
            print_test_result 10 "API Key Creation Test" "WARN"
        else
            KEY_CREATE_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/auth/api-keys \
              -H "Content-Type: application/json" \
              -H "X-CSRF-Token: $CSRF_TOKEN" \
              -c cookies.txt \
              -d '{"name": "test-key", "description": "Test API key"}' 2>&1)

            echo "Response:"
            echo "$KEY_CREATE_RESPONSE" | python -m json.tool 2>/dev/null || echo "$KEY_CREATE_RESPONSE"

            if echo "$KEY_CREATE_RESPONSE" | grep -q '"api_key"'; then
                print_test_result 10 "API Key Creation Test" "PASS"
                API_KEY=$(echo "$KEY_CREATE_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('api_key', ''))" 2>/dev/null)
            else
                print_test_result 10 "API Key Creation Test" "WARN"
            fi
        fi

        # Test 11: API Key Authentication Test
        print_test_start 11 "API Key Authentication Test"
        echo "Testing API key authentication..."

        if [ -z "$API_KEY" ]; then
            API_KEY="sk_harbor_test_key" # pragma: allowlist secret
            echo "Using placeholder API key for test"
        fi

        AUTH_RESPONSE=$(curl -s http://localhost:8080/api/v1/auth/me \
          -H "X-API-Key: $API_KEY" 2>&1)

        echo "Response:"
        echo "$AUTH_RESPONSE" | python -m json.tool 2>/dev/null || echo "$AUTH_RESPONSE"

        if echo "$AUTH_RESPONSE" | grep -q '"username"'; then
            print_test_result 11 "API Key Authentication Test" "PASS"
        else
            print_test_result 11 "API Key Authentication Test" "WARN"
        fi

    else
        echo -e "${RED}Server failed to start${NC}"
        echo "Server log:"
        cat "$SERVER_LOG"
        print_test_result 8 "Server Start" "FAIL"
    fi

    # Clean up
    cleanup_server
    rm -f "$SERVER_LOG" cookies.txt

else
    echo ""
    echo "Skipping server and API tests..."
fi

# Final summary
echo ""
print_summary

# Exit with appropriate code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Ready to commit and push to GitHub!"
    exit 0
else
    echo ""
    echo "⚠️  Please review warnings and failures before pushing"
    exit 1
fi
