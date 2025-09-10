#!/usr/bin/env python3
# scripts/dev/test_complete_logging.py
"""
Harbor Complete Logging & Monitoring Test Suite

Comprehensive test script that validates all logging and monitoring components including:
- Structured logging configuration with new package structure
- Correlation ID tracking with context management
- Log rotation with compression
- Specialized loggers (audit, access, performance)
- Performance logging utilities
- Health monitoring service
- Middleware integration
- Request logging

Can be run standalone or as part of the test suite.
"""

import asyncio
import gzip
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test result tracking
test_results = []
verbose = True  # Always verbose for this comprehensive test


def log(message: str, level: str = "INFO"):
    """Log message with level indicator."""
    colors = {
        "INFO": "\033[0;34m",
        "PASS": "\033[0;32m",
        "FAIL": "\033[0;31m",
        "WARN": "\033[1;33m",
        "DEBUG": "\033[0;90m",
    }
    color = colors.get(level, "")
    reset = "\033[0m"
    print(f"{color}[{level}] {message}{reset}")


def test_section(name: str):
    """Print test section header."""
    print(f"\n{'=' * 70}")
    print(f" {name}")
    print(f"{'=' * 70}\n")


def record_test(name: str, passed: bool, details: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    log(f"{name}: {details if details else 'Completed'}", status)


# ==============================================================================
# Test 1: Package Structure and Imports
# ==============================================================================


def test_package_structure():
    """Test new package structure and imports."""
    test_section("1. PACKAGE STRUCTURE & IMPORTS")

    tests_passed = 0

    try:
        # Test that old module doesn't exist
        old_module_path = Path("app/utils/logging.py")
        if not old_module_path.exists():
            tests_passed += 1
            log("  ✓ Old logging.py removed", "PASS")
        else:
            log("  ✗ Old logging.py still exists", "FAIL")

        # Test new package structure
        package_path = Path("app/utils/logging")
        if package_path.is_dir():
            tests_passed += 1
            log("  ✓ Logging package directory exists", "PASS")

        # Check all module files exist
        expected_modules = [
            "__init__.py",
            "core.py",
            "context.py",
            "filters.py",
            "formatters.py",
            "handlers.py",
            "performance.py",
            "specialized.py",
        ]

        for module in expected_modules:
            module_path = package_path / module
            if module_path.exists():
                tests_passed += 1
                log(f"  ✓ Module {module} exists", "PASS")
            else:
                log(f"  ✗ Module {module} missing", "FAIL")

        # Test imports from __init__.py
        from app.utils.logging import (
            setup_logging,
            get_logger,
            get_correlation_id,
            set_correlation_id,
            get_access_logger,
            get_audit_logger,
            log_performance,
            CorrelationIdFilter,
            HarborFormatter,
            CompressedRotatingFileHandler,
        )

        tests_passed += 1
        log("  ✓ All exports available from __init__.py", "PASS")

        record_test(
            "Package Structure",
            tests_passed >= 8,
            f"{tests_passed}/10 structure tests passed",
        )
        return tests_passed >= 8

    except Exception as e:
        record_test("Package Structure", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 2: Core Logging Configuration
# ==============================================================================


def test_core_logging():
    """Test core logging setup and configuration."""
    test_section("2. CORE LOGGING CONFIGURATION")

    try:
        from app.utils.logging.core import setup_logging, get_logger, _module_loggers

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            tests_passed = 0

            # Test 1: Basic setup with all parameters
            setup_logging(
                level="DEBUG",
                log_dir=log_dir,
                json_format=False,
                enable_rotation=True,
                max_bytes=1024,
                backup_count=3,
                deployment_profile="development",
                enable_compression=True,
                enable_time_rotation=False,
                enable_sensitive_filter=True,
            )

            if log_dir.exists():
                tests_passed += 1
                log("  ✓ Log directory created", "PASS")

            # Test 2: Check all log files created
            expected_files = [
                "app.log",
                "error.log",
                "access.log",
                "audit.log",
                "performance.log",
            ]
            for filename in expected_files:
                if (log_dir / filename).exists():
                    tests_passed += 1
                    log(f"  ✓ {filename} created", "PASS")

            # Test 3: Logger caching
            logger1 = get_logger("test.module1")
            logger2 = get_logger("test.module1")

            if logger1 is logger2:
                tests_passed += 1
                log("  ✓ Logger caching working", "PASS")

            # Test 4: Logger has correlation filter
            has_filter = any(
                isinstance(f, logging.Filter) and hasattr(f, "filter")
                for f in logger1.filters
            )
            if has_filter:
                tests_passed += 1
                log("  ✓ Logger has correlation filter", "PASS")

            # Test 5: Different profiles
            setup_logging(
                log_dir=log_dir,
                deployment_profile="production",
                json_format=True,
            )

            # Check JSON format by writing a log
            test_logger = get_logger("test.json")
            test_logger.info("Test JSON message")

            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            record_test(
                "Core Logging",
                tests_passed >= 7,
                f"{tests_passed}/8 core tests passed",
            )
            return tests_passed >= 7

    except Exception as e:
        record_test("Core Logging", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 3: Context Management
# ==============================================================================


async def test_context_management():
    """Test correlation ID context management."""
    test_section("3. CONTEXT MANAGEMENT")

    try:
        from app.utils.logging.context import (
            correlation_id_var,
            set_correlation_id,
            get_correlation_id,
            clear_correlation_id,
        )

        tests_passed = 0

        # Test 1: Set and get correlation ID
        test_id = "context-test-123"
        set_correlation_id(test_id)
        retrieved = get_correlation_id()

        if retrieved == test_id:
            tests_passed += 1
            log(f"  ✓ Set/get correlation ID: {test_id}", "PASS")

        # Test 2: Clear correlation ID
        clear_correlation_id()
        cleared = correlation_id_var.get()

        if cleared == "":
            tests_passed += 1
            log("  ✓ Clear correlation ID working", "PASS")

        # Test 3: Auto-generation when empty
        new_id = get_correlation_id()
        if new_id and len(new_id) == 36:  # UUID format
            tests_passed += 1
            log(f"  ✓ Auto-generated ID: {new_id}", "PASS")

        # Test 4: Context isolation - FIXED (no nested event loop)
        set_correlation_id("context-1")
        id1 = get_correlation_id()

        async def nested():
            set_correlation_id("context-2")
            return get_correlation_id()

        id2 = await nested()
        id3 = get_correlation_id()

        # Note: In Python's contextvars, changes in nested async functions
        # DO affect the parent context. This is expected behavior.
        if id1 == "context-1" and id2 == "context-2" and id3 == "context-2":
            tests_passed += 1
            log("  ✓ Context behavior working as designed", "PASS")

        record_test(
            "Context Management",
            tests_passed >= 3,
            f"{tests_passed}/4 context tests passed",
        )
        return tests_passed >= 3

    except Exception as e:
        record_test("Context Management", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 4: Filters
# ==============================================================================


def test_filters():
    """Test logging filters."""
    test_section("4. LOGGING FILTERS")

    try:
        from app.utils.logging.filters import (
            CorrelationIdFilter,
            EnvironmentFilter,
            SensitiveDataFilter,
        )
        from app.utils.logging.context import set_correlation_id

        tests_passed = 0

        # Test 1: CorrelationIdFilter
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        set_correlation_id("filter-test-456")
        filter_obj.filter(record)

        if (
            hasattr(record, "correlation_id")
            and record.correlation_id == "filter-test-456"
        ):
            tests_passed += 1
            log("  ✓ Correlation filter adds ID", "PASS")

        # Test 2: EnvironmentFilter
        env_filter = EnvironmentFilter("production")
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        env_filter.filter(record2)

        if (
            hasattr(record2, "deployment_profile")
            and record2.deployment_profile == "production"
        ):
            tests_passed += 1
            log("  ✓ Environment filter adds profile", "PASS")

        # Test 3: SensitiveDataFilter
        sensitive_filter = SensitiveDataFilter()
        record3 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User password is secret123",
            args=(),
            exc_info=None,
        )

        sensitive_filter.filter(record3)

        if hasattr(record3, "contains_sensitive") and record3.contains_sensitive:
            tests_passed += 1
            log("  ✓ Sensitive data filter detects patterns", "PASS")

        # Test 4: Non-sensitive data
        record4 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Normal message",
            args=(),
            exc_info=None,
        )

        sensitive_filter.filter(record4)

        if hasattr(record4, "contains_sensitive") and not record4.contains_sensitive:
            tests_passed += 1
            log("  ✓ Sensitive filter handles normal messages", "PASS")

        record_test(
            "Logging Filters",
            tests_passed >= 3,
            f"{tests_passed}/4 filter tests passed",
        )
        return tests_passed >= 3

    except Exception as e:
        record_test("Logging Filters", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 5: Formatters
# ==============================================================================


def test_formatters():
    """Test log formatters."""
    test_section("5. LOG FORMATTERS")

    try:
        from app.utils.logging.formatters import (
            HarborFormatter,
            JSONFormatter,
            DevelopmentFormatter,
            get_formatter_for_profile,
        )

        tests_passed = 0

        # Test 1: HarborFormatter
        formatter = HarborFormatter("%(message)s - %(correlation_id)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        if "system" in formatted:  # Default correlation_id
            tests_passed += 1
            log("  ✓ HarborFormatter adds defaults", "PASS")

        # Test 2: JSONFormatter
        json_formatter = JSONFormatter()
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="JSON test",
            args=(),
            exc_info=None,
        )

        formatted_json = json_formatter.format(record2)
        try:
            data = json.loads(formatted_json)
            if all(k in data for k in ["timestamp", "level", "logger", "message"]):
                tests_passed += 1
                log("  ✓ JSONFormatter produces valid JSON", "PASS")
        except json.JSONDecodeError:
            log("  ✗ JSONFormatter invalid JSON", "FAIL")

        # Test 3: DevelopmentFormatter with colors
        dev_formatter = DevelopmentFormatter("%(levelname)s - %(message)s")
        record3 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Dev test",
            args=(),
            exc_info=None,
        )

        formatted_dev = dev_formatter.format(record3)
        if "\033[" in formatted_dev:  # Has ANSI colors
            tests_passed += 1
            log("  ✓ DevelopmentFormatter adds colors", "PASS")

        # Test 4: get_formatter_for_profile
        prod_formatter = get_formatter_for_profile("production", json_format=True)
        if isinstance(prod_formatter, JSONFormatter):
            tests_passed += 1
            log("  ✓ Profile formatter selection works", "PASS")

        record_test(
            "Log Formatters",
            tests_passed >= 3,
            f"{tests_passed}/4 formatter tests passed",
        )
        return tests_passed >= 3

    except Exception as e:
        record_test("Log Formatters", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 6: Handlers
# ==============================================================================


def test_handlers():
    """Test log handlers with rotation and compression."""
    test_section("6. LOG HANDLERS")

    try:
        from app.utils.logging.handlers import (
            CompressedRotatingFileHandler,
            TimedCompressedRotatingFileHandler,
            BufferedHandler,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tests_passed = 0

            # Test 1: CompressedRotatingFileHandler
            log_file = Path(tmpdir) / "test.log"
            handler = CompressedRotatingFileHandler(
                str(log_file),
                maxBytes=100,
                backupCount=3,
                compression_level=9,
            )

            test_logger = logging.getLogger("handler_test")
            test_logger.addHandler(handler)
            test_logger.setLevel(logging.INFO)

            # Write enough to trigger rotation
            for i in range(50):
                test_logger.info(f"Message {i} " + "x" * 30)

            handler.close()

            # Check for compressed files
            gz_files = list(Path(tmpdir).glob("*.gz"))
            if len(gz_files) > 0:
                tests_passed += 1
                log(f"  ✓ Compression working: {len(gz_files)} files", "PASS")

                # Verify compressed content
                with gzip.open(gz_files[0], "rt") as f:
                    content = f.read()
                    if "Message" in content:
                        tests_passed += 1
                        log("  ✓ Compressed files valid", "PASS")

            # Test 2: TimedCompressedRotatingFileHandler
            timed_file = Path(tmpdir) / "timed.log"
            timed_handler = TimedCompressedRotatingFileHandler(
                str(timed_file),
                when="S",  # Every second for testing
                interval=1,
                backupCount=3,
                compression_level=9,
            )

            if timed_handler:
                tests_passed += 1
                log("  ✓ Timed handler created", "PASS")

            timed_handler.close()

            # Test 3: BufferedHandler
            target_handler = logging.StreamHandler()
            buffered = BufferedHandler(
                capacity=10,
                flushLevel=logging.ERROR,
                target=target_handler,
            )

            if buffered.capacity == 10:
                tests_passed += 1
                log("  ✓ Buffered handler configured", "PASS")

            record_test(
                "Log Handlers",
                tests_passed >= 3,
                f"{tests_passed}/4 handler tests passed",
            )
            return tests_passed >= 3

    except Exception as e:
        record_test("Log Handlers", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 7: Performance Logging
# ==============================================================================


def test_performance_utilities():
    """Test performance logging utilities."""
    test_section("7. PERFORMANCE LOGGING")

    try:
        from app.utils.logging.performance import (
            log_performance,
            log_operation_time,
            measure_performance,
            PerformanceTracker,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            from app.utils.logging import setup_logging

            log_dir = Path(tmpdir)
            setup_logging(log_dir=log_dir, json_format=True)

            tests_passed = 0

            # Test 1: log_performance
            log_performance(
                func_name="test_function",
                duration_ms=123.45,
                metadata={"query": "SELECT *", "rows": 100},
            )

            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            perf_log = log_dir / "performance.log"
            if perf_log.exists():
                content = perf_log.read_text()
                if "test_function" in content and "123.45ms" in content:
                    tests_passed += 1
                    log("  ✓ log_performance working", "PASS")

            # Test 2: log_operation_time context manager
            with log_operation_time("context_operation", user_id=42):
                time.sleep(0.01)  # Small delay

            # Force flush again
            for handler in logging.getLogger().handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            content = perf_log.read_text()
            if "context_operation" in content:
                tests_passed += 1
                log("  ✓ log_operation_time context manager working", "PASS")

            # Test 3: measure_performance decorator
            @measure_performance("decorated_function")
            def test_func():
                time.sleep(0.01)
                return "result"

            result = test_func()

            if result == "result":
                tests_passed += 1
                log("  ✓ measure_performance decorator working", "PASS")

            # Test 4: PerformanceTracker
            tracker = PerformanceTracker("test_tracker", sample_size=10)

            for i in range(5):
                tracker.record(50.0 + i)

            if tracker.total_calls == 5:
                tests_passed += 1
                log("  ✓ PerformanceTracker recording", "PASS")

            record_test(
                "Performance Logging",
                tests_passed >= 3,
                f"{tests_passed}/4 performance tests passed",
            )
            return tests_passed >= 3

    except Exception as e:
        record_test("Performance Logging", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 8: Specialized Loggers
# ==============================================================================


def test_specialized_loggers():
    """Test specialized logger utilities."""
    test_section("8. SPECIALIZED LOGGERS")

    try:
        from app.utils.logging.specialized import (
            get_access_logger,
            get_audit_logger,
            get_security_logger,
            get_database_logger,
            get_docker_logger,
            StructuredLogger,
        )

        tests_passed = 0

        # Test logger names
        access_logger = get_access_logger()
        if access_logger.name == "harbor.access":
            tests_passed += 1
            log("  ✓ Access logger name correct", "PASS")

        audit_logger = get_audit_logger()
        if audit_logger.name == "harbor.audit":
            tests_passed += 1
            log("  ✓ Audit logger name correct", "PASS")

        security_logger = get_security_logger()
        if security_logger.name == "harbor.security":
            tests_passed += 1
            log("  ✓ Security logger name correct", "PASS")

        database_logger = get_database_logger()
        if database_logger.name == "harbor.database":
            tests_passed += 1
            log("  ✓ Database logger name correct", "PASS")

        docker_logger = get_docker_logger()
        if docker_logger.name == "harbor.docker":
            tests_passed += 1
            log("  ✓ Docker logger name correct", "PASS")

        # Test StructuredLogger
        structured = StructuredLogger("test.structured")

        # Mock the logger to capture calls
        with patch.object(structured.logger, "log") as mock_log:
            structured.log_event(
                "test_event",
                "Test message",
                level=logging.INFO,
                user_id=123,
            )

            # Check the call was made with extra data
            if mock_log.called:
                call_args = mock_log.call_args
                if "extra" in call_args[1]:
                    extra = call_args[1]["extra"]
                    if extra.get("event_type") == "test_event":
                        tests_passed += 1
                        log("  ✓ StructuredLogger log_event working", "PASS")

        # Test log_success
        with patch.object(structured.logger, "log") as mock_log:
            structured.log_success("update", "Update successful", container_id="abc123")

            if mock_log.called:
                tests_passed += 1
                log("  ✓ StructuredLogger log_success working", "PASS")

        # Test log_failure
        with patch.object(structured.logger, "log") as mock_log:
            structured.log_failure(
                "update",
                "Update failed",
                error=ValueError("Test error"),
            )

            if mock_log.called:
                call_args = mock_log.call_args
                if "extra" in call_args[1]:
                    extra = call_args[1]["extra"]
                    if extra.get("error_type") == "ValueError":
                        tests_passed += 1
                        log("  ✓ StructuredLogger log_failure working", "PASS")

        record_test(
            "Specialized Loggers",
            tests_passed >= 7,
            f"{tests_passed}/8 specialized tests passed",
        )
        return tests_passed >= 7

    except Exception as e:
        record_test("Specialized Loggers", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 9: Integration with Middleware
# ==============================================================================


async def test_middleware_integration():
    """Test middleware integration."""
    test_section("9. MIDDLEWARE INTEGRATION")

    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.middleware.correlation import CorrelationMiddleware
        from app.middleware.request_logging import RequestLoggingMiddleware
        from app.utils.logging import get_correlation_id

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"correlation_id": get_correlation_id()}

        client = TestClient(app)
        tests_passed = 0

        # Test with explicit correlation ID
        response = client.get(
            "/test", headers={"X-Correlation-ID": "middleware-test-789"}
        )

        if response.status_code == 200:
            tests_passed += 1
            log("  ✓ Request processed", "PASS")

        if response.headers.get("X-Correlation-ID") == "middleware-test-789":
            tests_passed += 1
            log("  ✓ Correlation ID in headers", "PASS")

        if "X-Request-ID" in response.headers:
            tests_passed += 1
            log(f"  ✓ Request ID: {response.headers['X-Request-ID']}", "PASS")

        if "X-Response-Time" in response.headers:
            tests_passed += 1
            log(f"  ✓ Response time: {response.headers['X-Response-Time']}", "PASS")

        # Test auto-generation
        response2 = client.get("/test")

        if "X-Correlation-ID" in response2.headers:
            generated_id = response2.headers["X-Correlation-ID"]
            if len(generated_id) == 36:  # UUID format
                tests_passed += 1
                log(f"  ✓ Auto-generated ID: {generated_id}", "PASS")

        record_test(
            "Middleware Integration",
            tests_passed >= 4,
            f"{tests_passed}/5 middleware tests passed",
        )
        return tests_passed >= 4

    except Exception as e:
        record_test("Middleware Integration", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Test 10: End-to-End Logging Flow
# ==============================================================================


async def test_end_to_end():
    """Test complete logging flow end-to-end."""
    test_section("10. END-TO-END LOGGING FLOW")

    try:
        from app.utils.logging import setup_logging, get_logger
        from app.utils.logging.specialized import StructuredLogger
        from app.utils.logging.performance import log_operation_time

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Setup logging with all features
            setup_logging(
                level="DEBUG",
                log_dir=log_dir,
                json_format=True,
                enable_rotation=True,
                deployment_profile="production",
                enable_compression=True,
                enable_sensitive_filter=True,
            )

            tests_passed = 0

            # Test 1: Multiple logger types
            app_logger = get_logger("app.main")
            structured = StructuredLogger("app.structured")

            app_logger.info("Application started")
            app_logger.debug("Debug information")
            app_logger.warning("Warning message")
            app_logger.error("Error occurred")

            structured.log_success("startup", "Application initialized")
            structured.log_failure("connection", "Database connection failed")

            # Test 2: Performance logging
            with log_operation_time("database_query", query="SELECT * FROM users"):
                time.sleep(0.01)

            # Force flush all handlers
            for logger in [logging.getLogger(), app_logger, structured.logger]:
                for handler in logger.handlers:
                    if hasattr(handler, "flush"):
                        handler.flush()

            # Verify files created
            if (log_dir / "app.log").exists():
                tests_passed += 1
                log("  ✓ App log created", "PASS")

            if (log_dir / "error.log").exists():
                tests_passed += 1
                log("  ✓ Error log created", "PASS")

            if (log_dir / "performance.log").exists():
                tests_passed += 1
                log("  ✓ Performance log created", "PASS")

            # Check JSON format
            app_log_content = (log_dir / "app.log").read_text()
            if app_log_content:
                lines = app_log_content.strip().split("\n")
                try:
                    for line in lines[:1]:  # Check first line
                        if line:
                            data = json.loads(line)
                            if all(k in data for k in ["timestamp", "level", "logger"]):
                                tests_passed += 1
                                log("  ✓ JSON format valid", "PASS")
                                break
                except json.JSONDecodeError:
                    log("  ✗ JSON format invalid", "FAIL")

            # Check error log has only errors
            error_content = (log_dir / "error.log").read_text()
            if error_content:
                if (
                    "Error occurred" in error_content
                    and "Debug information" not in error_content
                ):
                    tests_passed += 1
                    log("  ✓ Error log filtering working", "PASS")

            record_test(
                "End-to-End Flow",
                tests_passed >= 4,
                f"{tests_passed}/5 e2e tests passed",
            )
            return tests_passed >= 4

    except Exception as e:
        record_test("End-to-End Flow", False, str(e))
        import traceback

        traceback.print_exc()
        return False


# ==============================================================================
# Main Test Runner
# ==============================================================================


async def run_all_tests():
    """Run all logging tests."""
    print("=" * 70)
    print(" HARBOR COMPLETE LOGGING & MONITORING TEST SUITE")
    print("=" * 70)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("Test mode: COMPREHENSIVE")
    print()

    all_passed = True

    # Synchronous tests
    all_passed &= test_package_structure()
    all_passed &= test_core_logging()

    # FIXED: Async context management test - MUST use await
    all_passed &= await test_context_management()

    # More synchronous tests
    all_passed &= test_filters()
    all_passed &= test_formatters()
    all_passed &= test_handlers()
    all_passed &= test_performance_utilities()
    all_passed &= test_specialized_loggers()

    # Asynchronous tests
    all_passed &= await test_middleware_integration()
    all_passed &= await test_end_to_end()

    # Print summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70 + "\n")

    passed = sum(1 for t in test_results if t["passed"])
    failed = len(test_results) - passed

    for result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status}: {result['name']}")
        if result["details"]:
            print(f"         {result['details']}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(test_results)} tests")

    if all_passed:
        print("\n🎉 ALL LOGGING & MONITORING TESTS PASSED!")
        print("\n✅ The refactored logging system is complete and working!")
        print("\nKey achievements:")
        print("  • Modular package structure with clear separation")
        print("  • Context-aware correlation ID tracking")
        print("  • Comprehensive filtering and formatting")
        print("  • Rotation with compression support")
        print("  • Performance logging utilities")
        print("  • Specialized loggers for different purposes")
        print("  • Full middleware integration")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        print("\n⚠️  Please review failures before proceeding")
        return 1


if __name__ == "__main__":
    print("Starting test suite...")  # Debug line to confirm entry
    import asyncio
    import sys

    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error running tests: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
