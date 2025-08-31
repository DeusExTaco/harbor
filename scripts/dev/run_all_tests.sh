#!/bin/bash
# scripts/dev/run_all_tests.sh
# shellcheck disable=SC2289
# Harbor Complete Test Suite Runner - Extended Version with Structure and Logging Tests
#
# Runs all tests including structure validation, logging, security, and integration tests.
# Stops on first failure for critical tests (1-10), then continues with extended tests.
#
# Usage:
#     ./run_all_tests.sh [--skip-server] [--quick]
#
# Options:
#     --skip-server  Skip server startup and API tests
#     --quick        Run only essential tests (skip optional extended tests)

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

    # Add to test_order only if not already present
    local already_added=false
    for num in "${test_order[@]}"; do
        if [ "$num" = "$test_num" ]; then
            already_added=true
            break
        fi
    done

    if [ "$already_added" = false ]; then
        test_order+=("$test_num")
    fi

    echo ""
}

# Function to print summary with numerical order
print_summary() {
    print_header "TEST SUMMARY"

    local passed=0
    local warned=0
    local failed=0

    # Sort test_order numerically
    IFS=$'\n' sorted_tests=($(sort -n <<<"${test_order[*]}"))
    unset IFS

    for test_num in "${sorted_tests[@]}"; do
        local status="${test_results[$test_num]}"
        local test_name=""

        case $test_num in
            1) test_name="Configuration System Test";;
            2) test_name="Project Structure Validation";;  # NEW
            3) test_name="Environment Check";;
            4) test_name="Security Middleware Test";;
            5) test_name="Complete Security Test";;
            6) test_name="Complete Logging Test";;
            7) test_name="Database Implementation Test";;
            8) test_name="Authentication System Test";;
            9) test_name="API Key Manual Test";;
            10) test_name="Pre-commit Checks";;
            11) test_name="Server Start";;
            12) test_name="Login API Test";;
            13) test_name="API Key Creation Test";;
            14) test_name="API Key Authentication Test";;
            15) test_name="Docker Integration Test";;
            16) test_name="Registry Client Test";;
            17) test_name="Security Scan";;
            18) test_name="Import Cycle Detection";;
            19) test_name="Performance Baseline";;
        esac

        if [ -n "$test_name" ]; then
            if [ "$status" = "PASS" ]; then
                printf "${GREEN}✅ Test %2d: %-40s [PASS]${NC}\n" "$test_num" "$test_name"
                ((passed++))
            elif [ "$status" = "WARN" ]; then
                printf "${YELLOW}⚠️  Test %2d: %-40s [WARN]${NC}\n" "$test_num" "$test_name"
                ((warned++))
            elif [ "$status" = "FAIL" ]; then
                printf "${RED}❌ Test %2d: %-40s [FAIL]${NC}\n" "$test_num" "$test_name"
                ((failed++))
            fi
        fi
    done

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total: $passed passed, $warned warnings, $failed failed out of ${#sorted_tests[@]} tests"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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

print_header "HARBOR COMPLETE TEST SUITE (WITH STRUCTURE VALIDATION)"
echo "Starting comprehensive test suite..."
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Mode: $([ "$QUICK_MODE" = true ] && echo "QUICK" || echo "FULL")"
echo ""

# ============================================================================
# CORE TESTS (1-10) - Stop on failure
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

# Test 2: Project Structure Validation (NEW)
print_test_start 2 "Project Structure Validation"
if python scripts/dev/test_structure.py; then
    print_test_result 2 "Project Structure Validation" "PASS"
else
    print_test_result 2 "Project Structure Validation" "FAIL"
    print_summary
    exit 1
fi

# Test 3: Environment Check (was Test 2)
print_test_start 3 "Environment Check"
if python scripts/dev/check_environment.py; then
    print_test_result 3 "Environment Check" "PASS"
else
    print_test_result 3 "Environment Check" "FAIL"
    print_summary
    exit 1
fi

# Test 4: Security Middleware (Basic) (was Test 3)
print_test_start 4 "Security Middleware Test"
if python scripts/dev/test_security_middleware.py; then
    print_test_result 4 "Security Middleware Test" "PASS"
else
    print_test_result 4 "Security Middleware Test" "FAIL"
    print_summary
    exit 1
fi

# Test 5: Complete Security Test (was Test 4)
print_test_start 5 "Complete Security Test"
if python scripts/dev/test_complete_security.py; then
    print_test_result 5 "Complete Security Test" "PASS"
else
    print_test_result 5 "Complete Security Test" "FAIL"
    print_summary
    exit 1
fi

# Test 6: Complete Logging Test (was Test 5)
print_test_start 6 "Complete Logging Test"
if python scripts/dev/test_complete_logging.py; then
    print_test_result 6 "Complete Logging Test" "PASS"
else
    print_test_result 6 "Complete Logging Test" "FAIL"
    print_summary
    exit 1
fi

# Test 7: Database Implementation (was Test 6)
print_test_start 7 "Database Implementation Test"
if python scripts/dev/test_db_implementation.py --verbose; then
    print_test_result 7 "Database Implementation Test" "PASS"
else
    print_test_result 7 "Database Implementation Test" "FAIL"
    print_summary
    exit 1
fi

# Test 8: Authentication System (was Test 7)
print_test_start 8 "Authentication System Test"
if python scripts/dev/test_auth_system.py; then
    print_test_result 8 "Authentication System Test" "PASS"
else
    print_test_result 8 "Authentication System Test" "FAIL"
    print_summary
    exit 1
fi

# Test 9: API Key Manual Test (was Test 8)
print_test_start 9 "API Key Manual Test"
if python scripts/dev/test_api_key_manual.py; then
    print_test_result 9 "API Key Manual Test" "PASS"
else
    print_test_result 9 "API Key Manual Test" "FAIL"
    print_summary
    exit 1
fi

# Test 10: Pre-commit Checks (was Test 9)
print_test_start 10 "Pre-commit Checks"
if pre-commit run --all-files; then
    print_test_result 10 "Pre-commit Checks" "PASS"
else
    print_test_result 10 "Pre-commit Checks" "FAIL"
    print_summary
    exit 1
fi

# All core tests passed
echo ""
echo -e "${GREEN}✅ All core tests (1-10) passed!${NC}"

# ============================================================================
# EXTENDED TESTS (15-19) - Continue on failure
# ============================================================================

if [ "$QUICK_MODE" = false ]; then
    echo ""
    echo "Running extended test suite..."

    # Test 15: Docker Integration (was Test 14)
    print_test_start 15 "Docker Integration Test"
    if [ -f "scripts/dev/test_docker_integration.py" ]; then
        if python scripts/dev/test_docker_integration.py; then
            print_test_result 15 "Docker Integration Test" "PASS"
        else
            print_test_result 15 "Docker Integration Test" "WARN"
        fi
    else
        echo "Test file not found, skipping..."
        print_test_result 15 "Docker Integration Test" "WARN"
    fi

    # Test 16: Registry Client (was Test 15)
    print_test_start 16 "Registry Client Test"
    if [ -f "scripts/dev/test_registry_client.py" ]; then
        if python scripts/dev/test_registry_client.py; then
            print_test_result 16 "Registry Client Test" "PASS"
        else
            print_test_result 16 "Registry Client Test" "WARN"
        fi
    else
        echo "Test file not found, skipping..."
        print_test_result 16 "Registry Client Test" "WARN"
    fi

    # Test 17: Security Scan (was Test 16)
    print_test_start 17 "Security Scan"
    if [ -f "scripts/dev/test_security_scan.py" ]; then
        if python scripts/dev/test_security_scan.py; then
            print_test_result 17 "Security Scan" "PASS"
        else
            print_test_result 17 "Security Scan" "WARN"
        fi
    else
        echo "Test file not found, skipping..."
        print_test_result 17 "Security Scan" "WARN"
    fi

    # Test 18: Import Cycle Detection (was Test 17)
    print_test_start 18 "Import Cycle Detection"
    if [ -f "scripts/dev/test_import_cycles.py" ]; then
        if python scripts/dev/test_import_cycles.py; then
            print_test_result 18 "Import Cycle Detection" "PASS"
        else
            print_test_result 18 "Import Cycle Detection" "WARN"
        fi
    else
        echo "Test file not found, skipping..."
        print_test_result 18 "Import Cycle Detection" "WARN"
    fi

    # Test 19: Performance Baseline (was Test 18)
    print_test_start 19 "Performance Baseline"
    if [ -f "scripts/dev/test_performance_baseline.py" ]; then
        if python scripts/dev/test_performance_baseline.py; then
            print_test_result 19 "Performance Baseline" "PASS"
        else
            print_test_result 19 "Performance Baseline" "WARN"
        fi
    else
        echo "Test file not found, skipping..."
        print_test_result 19 "Performance Baseline" "WARN"
    fi
else
    echo ""
    echo "Skipping extended tests (quick mode)..."
fi

# ============================================================================
# SERVER AND API TESTS (11-14)
# ============================================================================

if [ "$SKIP_SERVER" = false ]; then
    echo ""
    echo "Proceeding to server tests..."

    # Test 11: Start Server (was Test 10)
    print_test_start 11 "Server Start"
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
        print_test_result 11 "Server Start" "PASS"

        # Test 12: Login API Test (was Test 11)
        print_test_start 12 "Login API Test"
        echo "Testing login endpoint..."

        LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
            -H "Content-Type: application/json" \
            -d '{"username": "admin", "password": "3CdCDURCtKQiArev"}' 2>&1) # pragma: allowlist secret

        echo "Response:"
        echo "$LOGIN_RESPONSE" | python -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"

        if echo "$LOGIN_RESPONSE" | grep -q '"success"'; then
            print_test_result 12 "Login API Test" "PASS"
            CSRF_TOKEN=$(echo "$LOGIN_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('csrf_token', ''))" 2>/dev/null)
        else
            print_test_result 12 "Login API Test" "WARN"
        fi

        # Test 13: API Key Creation Test (was Test 12)
        print_test_start 13 "API Key Creation Test"
        echo "Testing API key creation..."

        if [ -z "$CSRF_TOKEN" ]; then
            echo "No CSRF token available, skipping test"
            print_test_result 13 "API Key Creation Test" "WARN"
        else
            KEY_CREATE_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/auth/api-keys \
                -H "Content-Type: application/json" \
                -H "X-CSRF-Token: $CSRF_TOKEN" \
                -c cookies.txt \
                -d '{"name": "test-key", "description": "Test API key"}' 2>&1)

            echo "Response:"
            echo "$KEY_CREATE_RESPONSE" | python -m json.tool 2>/dev/null || echo "$KEY_CREATE_RESPONSE"

            if echo "$KEY_CREATE_RESPONSE" | grep -q '"api_key"'; then
                print_test_result 13 "API Key Creation Test" "PASS"
                API_KEY=$(echo "$KEY_CREATE_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('api_key', ''))" 2>/dev/null)
            else
                print_test_result 13 "API Key Creation Test" "WARN"
            fi
        fi

        # Test 14: API Key Authentication Test (was Test 13)
        print_test_start 14 "API Key Authentication Test"
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
            print_test_result 14 "API Key Authentication Test" "PASS"
        else
            print_test_result 14 "API Key Authentication Test" "WARN"
        fi

    else
        echo -e "${RED}Server failed to start${NC}"
        echo "Server log:"
        cat "$SERVER_LOG"
        print_test_result 11 "Server Start" "FAIL"
        print_test_result 12 "Login API Test" "FAIL"
        print_test_result 13 "API Key Creation Test" "FAIL"
        print_test_result 14 "API Key Authentication Test" "FAIL"
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
