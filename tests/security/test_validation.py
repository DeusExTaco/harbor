# tests/unit/security/test_validation.py
"""Unit tests for input validation and sanitization."""

import pytest
from pydantic import ValidationError

from app.security.validation import (
    ConfigurationValidator,
    ContainerIdentifier,
    ImageReference,
    InputSanitizer,
    RequestValidator,
    ScheduleTime,
    SecurityValidationError,
    URLReference,
)


class TestInputSanitizer:
    """Test input sanitization functions."""

    def test_sanitize_html(self):
        """Test HTML sanitization prevents XSS."""
        sanitizer = InputSanitizer()

        # Test script tag removal
        dangerous = "<script>alert('xss')</script>Hello"
        safe = sanitizer.sanitize_html(dangerous)
        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe
        assert "Hello" in safe

        # Test event handler removal
        dangerous = "<img src='x' onerror='alert(1)'>"
        safe = sanitizer.sanitize_html(dangerous)
        assert "onerror" not in safe
        assert "&lt;img" in safe

        # Test normal text passes through
        normal = "Just normal text"
        assert sanitizer.sanitize_html(normal) == normal

    def test_sanitize_path(self):
        """Test path sanitization prevents traversal."""
        sanitizer = InputSanitizer()

        # Test path traversal detection
        with pytest.raises(SecurityValidationError) as exc:
            sanitizer.sanitize_path("../../etc/passwd")
        assert "traversal" in str(exc.value).lower()

        with pytest.raises(SecurityValidationError):
            sanitizer.sanitize_path("..\\..\\windows\\system32")

        # Test absolute path rejection when not allowed
        with pytest.raises(SecurityValidationError) as exc:
            sanitizer.sanitize_path("/etc/passwd", allow_absolute=False)
        assert "absolute" in str(exc.value).lower()

        # Test valid relative path
        valid_path = "data/config.json"
        result = sanitizer.sanitize_path(valid_path)
        assert ".." not in result

    def test_sanitize_container_name(self):
        """Test container name validation."""
        sanitizer = InputSanitizer()

        # Valid names
        valid_names = [
            "nginx-proxy",
            "web_server",
            "app123",
            "test.container",
            "a",  # Single character
        ]
        for name in valid_names:
            assert sanitizer.sanitize_container_name(name) == name

        # Invalid names
        invalid_cases = [
            ("", "empty"),
            ("invalid/name", "invalid characters"),
            ("$malicious", "special characters"),
            ("-startwithdash", "invalid start"),
            ("a" * 256, "too long"),
            ("container|name", "pipe character"),
        ]

        for name, reason in invalid_cases:
            with pytest.raises(SecurityValidationError) as exc:
                sanitizer.sanitize_container_name(name)
            # Verify we get meaningful error messages
            assert exc.value.field == "container_name"

    def test_sanitize_image_reference(self):
        """Test Docker image reference validation."""
        sanitizer = InputSanitizer()

        # Valid references
        valid_refs = [
            "nginx:latest",
            "docker.io/library/nginx:1.21",
            "ghcr.io/user/image:v1.0.0",
            "localhost:5000/myimage",
            "image@sha256:abc123",
        ]
        for ref in valid_refs:
            assert sanitizer.sanitize_image_reference(ref) == ref

        # Invalid references
        invalid_refs = [
            "image$(whoami)",  # Command injection
            "image`id`",  # Backticks
            "image;ls",  # Semicolon
            "image&&pwd",  # Shell operators
            "image|cat",  # Pipe
        ]

        for ref in invalid_refs:
            with pytest.raises(SecurityValidationError) as exc:
                sanitizer.sanitize_image_reference(ref)
            assert "dangerous character" in str(exc.value)

    def test_sanitize_url(self):
        """Test URL sanitization."""
        sanitizer = InputSanitizer()

        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://localhost:8080/path",
            "https://registry-1.docker.io/v2/",
        ]
        for url in valid_urls:
            result = sanitizer.sanitize_url(url)
            assert result  # Should return normalized URL

        # Invalid schemes
        with pytest.raises(SecurityValidationError) as exc:
            sanitizer.sanitize_url("javascript:alert(1)")
        assert "scheme" in str(exc.value).lower()

        with pytest.raises(SecurityValidationError):
            sanitizer.sanitize_url("file:///etc/passwd")

        # Custom allowed schemes
        ftp_url = "ftp://example.com/file"
        with pytest.raises(SecurityValidationError):
            sanitizer.sanitize_url(ftp_url)  # FTP not in default schemes

        # Allow FTP explicitly
        result = sanitizer.sanitize_url(ftp_url, allowed_schemes=["ftp"])
        assert result == ftp_url

    def test_sanitize_sql_input(self):
        """Test SQL injection pattern detection."""
        sanitizer = InputSanitizer()

        # Safe inputs
        safe_inputs = [
            "normal_value",
            "user@example.com",
            "123456",
            "some-id-here",
        ]
        for value in safe_inputs:
            assert sanitizer.sanitize_sql_input(value) == value

        # Dangerous patterns (these are for defense-in-depth, real protection is parameterized queries)
        dangerous_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords",
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(SecurityValidationError) as exc:
                sanitizer.sanitize_sql_input(pattern)
            assert "SQL pattern" in str(exc.value)

    def test_validate_json_structure(self):
        """Test JSON structure validation for DoS prevention."""
        sanitizer = InputSanitizer()

        # Valid JSON structures
        valid_json = {"key1": "value1", "key2": {"nested": "value"}, "list": [1, 2, 3]}
        assert sanitizer.validate_json_structure(valid_json) == valid_json

        # Too deeply nested
        def create_nested(depth):
            if depth == 0:
                return "value"
            return {"nested": create_nested(depth - 1)}

        too_deep = create_nested(15)  # Exceeds default max_depth of 10
        with pytest.raises(SecurityValidationError) as exc:
            sanitizer.validate_json_structure(too_deep)
        assert "too deep" in str(exc.value)

        # Too many keys
        too_many_keys = {f"key{i}": i for i in range(2000)}
        with pytest.raises(SecurityValidationError) as exc:
            sanitizer.validate_json_structure(too_many_keys)
        assert "too complex" in str(exc.value)


class TestValidationModels:
    """Test Pydantic validation models."""

    def test_container_identifier(self):
        """Test container identifier validation."""
        # Valid container
        container = ContainerIdentifier(
            uid="550e8400-e29b-41d4-a716-446655440000", name="nginx-proxy"
        )
        assert container.uid == "550e8400-e29b-41d4-a716-446655440000"
        assert container.name == "nginx-proxy"

        # Invalid UID format
        with pytest.raises(ValidationError) as exc:
            ContainerIdentifier(uid="not-a-uuid", name="test")
        assert "uid" in str(exc.value).lower()

        # Invalid name
        with pytest.raises(ValidationError):
            ContainerIdentifier(
                uid="550e8400-e29b-41d4-a716-446655440000", name="invalid/name"
            )

    def test_image_reference(self):
        """Test image reference validation."""
        # Valid reference
        image = ImageReference(reference="nginx:1.21-alpine")
        assert image.reference == "nginx:1.21-alpine"

        # Too long
        with pytest.raises(ValidationError):
            ImageReference(reference="x" * 1001)

        # Empty
        with pytest.raises(ValidationError):
            ImageReference(reference="")

    def test_schedule_time(self):
        """Test schedule time validation."""
        # Valid time
        schedule = ScheduleTime(time="03:00", timezone="UTC")
        assert schedule.time == "03:00"
        assert schedule.timezone == "UTC"

        # Invalid time format
        with pytest.raises(ValidationError):
            ScheduleTime(time="25:00")  # Invalid hour

        with pytest.raises(ValidationError):
            ScheduleTime(time="12:60")  # Invalid minute

        with pytest.raises(ValidationError):
            ScheduleTime(time="3:00")  # Missing leading zero

    def test_url_reference(self):
        """Test URL reference validation."""
        # Valid URL
        url = URLReference(url="https://example.com/api")
        assert url.url == "https://example.com/api"

        # Too long
        with pytest.raises(ValidationError):
            URLReference(url="https://example.com/" + "x" * 2000)


class TestRequestValidator:
    """Test request validation utilities."""

    def test_validate_pagination_params(self):
        """Test pagination parameter validation."""
        validator = RequestValidator()

        # Valid pagination
        page, per_page = validator.validate_pagination_params(1, 20)
        assert page == 1
        assert per_page == 20

        # Invalid page
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_pagination_params(0, 20)
        assert "page must be >= 1" in str(exc.value)

        with pytest.raises(SecurityValidationError):
            validator.validate_pagination_params(10001, 20)  # Too large

        # Invalid per_page
        with pytest.raises(SecurityValidationError):
            validator.validate_pagination_params(1, 0)

        with pytest.raises(SecurityValidationError):
            validator.validate_pagination_params(1, 101)  # Exceeds max

    def test_validate_sort_params(self):
        """Test sort parameter validation."""
        validator = RequestValidator()

        # Valid sort
        field, order = validator.validate_sort_params(
            "name", "asc", ["name", "created"]
        )
        assert field == "name"
        assert order == "asc"

        # Invalid order
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_sort_params("name", "invalid")
        assert "asc" in str(exc.value)

        # Field not in allowed list
        with pytest.raises(SecurityValidationError):
            validator.validate_sort_params("password", "asc", ["name", "created"])

        # SQL injection attempt in field
        with pytest.raises(SecurityValidationError):
            validator.validate_sort_params("name; DROP TABLE", "asc")

    def test_validate_time_range(self):
        """Test time range validation."""
        validator = RequestValidator()

        # Valid range
        start = "2024-01-01T00:00:00Z"
        end = "2024-01-02T00:00:00Z"
        result_start, result_end = validator.validate_time_range(start, end)
        assert result_start == start
        assert result_end == end

        # Invalid format
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_time_range("not-a-date", end)
        assert "format" in str(exc.value).lower()

        # Start after end
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_time_range(end, start)
        assert "before" in str(exc.value)

        # Range too large
        start = "2024-01-01T00:00:00Z"
        end = "2024-12-31T00:00:00Z"  # Almost a year
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_time_range(start, end, max_range_days=90)
        assert "too large" in str(exc.value)


class TestConfigurationValidator:
    """Test configuration value validation."""

    def test_validate_update_time(self):
        """Test update time format validation."""
        validator = ConfigurationValidator()

        # Valid times
        assert validator.validate_update_time("03:00") == "03:00"
        assert validator.validate_update_time("00:00") == "00:00"
        assert validator.validate_update_time("23:59") == "23:59"

        # Invalid times
        with pytest.raises(SecurityValidationError):
            validator.validate_update_time("24:00")

        with pytest.raises(SecurityValidationError):
            validator.validate_update_time("3:00")  # Missing zero

        with pytest.raises(SecurityValidationError):
            validator.validate_update_time("12:60")

    def test_validate_interval_seconds(self):
        """Test interval validation."""
        validator = ConfigurationValidator()

        # Valid intervals
        assert validator.validate_interval_seconds(60) == 60
        assert validator.validate_interval_seconds(3600) == 3600
        assert validator.validate_interval_seconds(604800) == 604800  # 1 week

        # Too short
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_interval_seconds(59)
        assert "too short" in str(exc.value).lower()

        # Too long
        with pytest.raises(SecurityValidationError) as exc:
            validator.validate_interval_seconds(604801)
        assert "too long" in str(exc.value).lower()

    def test_validate_timezone(self):
        """Test timezone validation."""
        validator = ConfigurationValidator()

        # Valid timezones
        assert validator.validate_timezone("UTC") == "UTC"
        assert validator.validate_timezone("America/New_York") == "America/New_York"
        assert validator.validate_timezone("Europe/London") == "Europe/London"

        # Invalid format
        with pytest.raises(SecurityValidationError):
            validator.validate_timezone("Invalid@Timezone")

        # Too long
        with pytest.raises(SecurityValidationError):
            validator.validate_timezone("A" * 51)


def test_security_validation_error():
    """Test SecurityValidationError exception."""
    error = SecurityValidationError(
        message="Test error", field="test_field", value="bad_value"
    )

    assert str(error) == "Test error"
    assert error.field == "test_field"
    assert error.value == "bad_value"
