"""
Harbor Container Updater - Input Validation and Sanitization

Implements comprehensive input validation and sanitization for security.
Following Harbor architecture design principles and security best practices.

Implementation: M0 Milestone - Foundation Phase
Part of: Authentication Foundation (v1: Simple)

Features:
- Request data validation and sanitization
- XSS prevention and HTML escaping
- SQL injection prevention
- Path traversal protection
- Container name and image validation
- Configuration value validation
"""

import html
import re
import urllib.parse
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator


class SecurityValidationError(Exception):
    """Exception raised for security validation failures."""

    def __init__(self, message: str, field: str = "", value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class InputSanitizer:
    """
    Input sanitization utilities for Harbor.

    Provides methods to sanitize various types of input to prevent
    security vulnerabilities like XSS, SQL injection, and path traversal.
    """

    @staticmethod
    def sanitize_html(value: Any, allow_basic_tags: bool = False) -> str:
        """
        Sanitize HTML input to prevent XSS attacks.

        Args:
            value: Input that may contain HTML (will be converted to string)
            allow_basic_tags: Whether to allow basic safe HTML tags

        Returns:
            Sanitized string safe for HTML output
        """
        # Convert to string if needed
        str_value = str(value) if not isinstance(value, str) else value

        # Simple approach - just escape HTML and return
        # TODO: Use bleach library for production-grade HTML sanitization with tags
        return html.escape(str_value, quote=True)

    @staticmethod
    def sanitize_path(value: str, allow_absolute: bool = False) -> str:
        """
        Sanitize file path to prevent path traversal attacks.

        Args:
            value: Input path string
            allow_absolute: Whether to allow absolute paths

        Returns:
            Sanitized path string

        Raises:
            SecurityValidationError: If path contains traversal attempts
        """
        # Input type check
        if not isinstance(value, str):
            raise SecurityValidationError("Path must be a string", "path", value)

        # Check for path traversal attempts
        if ".." in value or "/.." in value or "\\..\\" in value:
            raise SecurityValidationError(
                "Path traversal attempt detected", "path", value
            )

        # Check for absolute paths if not allowed
        if not allow_absolute:
            path_obj = Path(value)
            if path_obj.is_absolute():
                raise SecurityValidationError(
                    "Absolute paths not allowed", "path", value
                )

        # Path validation successful - return normalized path
        try:
            path_obj = Path(value)
            resolved = path_obj.resolve()
            return str(resolved)
        except (OSError, ValueError) as e:
            raise SecurityValidationError(
                f"Path resolution failed: {e!s}", "path", value
            ) from e

    @staticmethod
    def sanitize_container_name(value: str) -> str:
        """
        Sanitize Docker container name.

        Args:
            value: Container name to sanitize

        Returns:
            Sanitized container name

        Raises:
            SecurityValidationError: If name is invalid
        """
        # Type validation
        if not isinstance(value, str):
            raise SecurityValidationError(
                "Container name must be a string", "container_name", value
            )

        # Empty check
        if not value:
            raise SecurityValidationError(
                "Container name cannot be empty", "container_name", value
            )

        # Length check
        if len(value) > 255:
            raise SecurityValidationError(
                "Container name too long", "container_name", value
            )

        # Character validation - Docker container name rules:
        # - Must contain only [a-zA-Z0-9][a-zA-Z0-9_.-]
        # - Must start with alphanumeric
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", value):
            raise SecurityValidationError(
                "Container name contains invalid characters", "container_name", value
            )

        # All validations passed
        return value

    @staticmethod
    def sanitize_image_reference(value: str) -> str:
        """
        Sanitize Docker image reference.

        Args:
            value: Image reference to sanitize

        Returns:
            Sanitized image reference

        Raises:
            SecurityValidationError: If reference is invalid
        """
        # Type check
        if not isinstance(value, str):
            raise SecurityValidationError(
                "Image reference must be a string", "image", value
            )

        # Empty check
        if not value:
            raise SecurityValidationError(
                "Image reference cannot be empty", "image", value
            )

        # Length check
        if len(value) > 1000:
            raise SecurityValidationError("Image reference too long", "image", value)

        # Check for dangerous characters
        dangerous_chars = ["`", "$", ";", "&", "|", ">", "<", "(", ")", "{", "}"]
        for char in dangerous_chars:
            if char in value:
                raise SecurityValidationError(
                    f"Image reference contains dangerous character: {char}",
                    "image",
                    value,
                )

        # All checks passed
        return value

    @staticmethod
    def sanitize_url(value: str, allowed_schemes: list[str] | None = None) -> str:
        """
        Sanitize URL input.

        Args:
            value: URL to sanitize
            allowed_schemes: List of allowed URL schemes (default: http, https)

        Returns:
            Sanitized URL

        Raises:
            SecurityValidationError: If URL is invalid or uses disallowed scheme
        """
        if not isinstance(value, str):
            raise SecurityValidationError("URL must be a string", "url", value)

        if not value:
            return value

        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        try:
            parsed = urllib.parse.urlparse(value)

            # Check scheme
            if parsed.scheme and parsed.scheme.lower() not in allowed_schemes:
                raise SecurityValidationError(
                    f"URL scheme '{parsed.scheme}' not allowed", "url", value
                )

            # Reconstruct normalized URL
            normalized = urllib.parse.urlunparse(parsed)
            return normalized

        except Exception as e:
            raise SecurityValidationError(
                f"Invalid URL format: {e!s}", "url", value
            ) from e

    @staticmethod
    def sanitize_sql_input(value: Any) -> str:
        """
        Sanitize input that might be used in SQL contexts.

        Note: This is a defense-in-depth measure. Primary SQL injection
        prevention should use parameterized queries.

        Args:
            value: Input that might be used in SQL (will be converted to string)

        Returns:
            Sanitized input

        Raises:
            SecurityValidationError: If dangerous SQL patterns detected
        """
        # Convert to string if needed
        str_value = str(value) if not isinstance(value, str) else value

        # Define dangerous SQL patterns
        sql_patterns = [
            r"('|(\\'))+.*?((\\')+'|')",  # SQL string concatenation
            r"(;)\s*(drop|alter|create|delete|insert|update|select)",  # SQL commands
            r"(union\s+select)",  # UNION SELECT
            r"(or\s+1\s*=\s*1)",  # OR 1=1
            r"(-{2}|#)",  # SQL comments
        ]

        # Check for dangerous patterns using simple approach
        for pattern in sql_patterns:
            if re.search(pattern, str_value, re.IGNORECASE):
                raise SecurityValidationError(
                    "Potentially dangerous SQL pattern detected", "sql_input", str_value
                )

        # No dangerous patterns found - return value as-is
        return str_value

    @staticmethod
    def validate_json_structure(
        value: Any, max_depth: int = 10, max_keys: int = 1000
    ) -> Any:
        """
        Validate JSON structure to prevent DoS attacks.

        Args:
            value: JSON value to validate
            max_depth: Maximum nesting depth
            max_keys: Maximum number of keys

        Returns:
            Validated JSON value

        Raises:
            SecurityValidationError: If JSON structure is dangerous
        """

        def count_depth_and_keys(obj: Any, current_depth: int = 0) -> int:
            if current_depth > max_depth:
                raise SecurityValidationError(
                    f"JSON nesting too deep (max {max_depth})", "json", obj
                )

            key_count = 0

            if isinstance(obj, dict):
                key_count += len(obj)
                for v in obj.values():
                    key_count += count_depth_and_keys(v, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    key_count += count_depth_and_keys(item, current_depth + 1)

            return key_count

        total_keys = count_depth_and_keys(value)
        if total_keys > max_keys:
            raise SecurityValidationError(
                f"JSON too complex ({total_keys} keys, max {max_keys})", "json", value
            )

        return value


# =============================================================================
# Validation Models
# =============================================================================


class ContainerIdentifier(BaseModel):
    """Validated container identifier."""

    uid: str = Field(..., min_length=1, max_length=36)
    name: str = Field(..., min_length=1, max_length=255)

    @validator("name")
    def validate_container_name(cls, v: str) -> str:
        return InputSanitizer.sanitize_container_name(v)

    @validator("uid")
    def validate_uid_format(cls, v: str) -> str:
        # Basic UUID format validation
        if not re.match(r"^[0-9a-f-]{36}$", v.lower()):
            raise ValueError("Invalid UID format")
        return v.lower()


class ImageReference(BaseModel):
    """Validated Docker image reference."""

    reference: str = Field(..., min_length=1, max_length=1000)

    @validator("reference")
    def validate_image_reference(cls, v: str) -> str:
        return InputSanitizer.sanitize_image_reference(v)


class ScheduleTime(BaseModel):
    """Validated schedule time."""

    time: str = Field(..., pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="UTC", max_length=50)


class URLReference(BaseModel):
    """Validated URL reference."""

    url: str = Field(..., max_length=2000)

    @validator("url")
    def validate_url(cls, v: str) -> str:
        return InputSanitizer.sanitize_url(v)


# =============================================================================
# Request Validation Middleware
# =============================================================================


class RequestValidator:
    """
    Request validation utilities.

    Provides methods to validate common request patterns and data types.
    """

    @staticmethod
    def validate_pagination_params(
        page: int = 1, per_page: int = 20, max_per_page: int = 100
    ) -> tuple[int, int]:
        """
        Validate pagination parameters.

        Args:
            page: Page number
            per_page: Items per page
            max_per_page: Maximum allowed items per page

        Returns:
            Tuple of validated (page, per_page)

        Raises:
            SecurityValidationError: If parameters are invalid
        """
        if page < 1:
            raise SecurityValidationError("Page must be >= 1", "page", page)

        if page > 10000:  # Prevent excessive pagination
            raise SecurityValidationError("Page number too large", "page", page)

        if per_page < 1:
            raise SecurityValidationError("per_page must be >= 1", "per_page", per_page)

        if per_page > max_per_page:
            raise SecurityValidationError(
                f"per_page must be <= {max_per_page}", "per_page", per_page
            )

        return page, per_page

    @staticmethod
    def validate_sort_params(
        sort_field: str,
        sort_order: str = "asc",
        allowed_fields: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Validate sorting parameters.

        Args:
            sort_field: Field to sort by
            sort_order: Sort order (asc/desc)
            allowed_fields: List of allowed sort fields

        Returns:
            Tuple of validated (sort_field, sort_order)

        Raises:
            SecurityValidationError: If parameters are invalid
        """
        if sort_order.lower() not in ["asc", "desc"]:
            raise SecurityValidationError(
                "sort_order must be 'asc' or 'desc'", "sort_order", sort_order
            )

        if allowed_fields and sort_field not in allowed_fields:
            raise SecurityValidationError(
                f"sort_field must be one of: {', '.join(allowed_fields)}",
                "sort_field",
                sort_field,
            )

        # Sanitize field name (prevent SQL injection in ORDER BY)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", sort_field):
            raise SecurityValidationError(
                "Invalid sort field format", "sort_field", sort_field
            )

        return sort_field, sort_order.lower()

    @staticmethod
    def validate_time_range(
        start_time: str | None = None,
        end_time: str | None = None,
        max_range_days: int = 90,
    ) -> tuple[str | None, str | None]:
        """
        Validate time range parameters.

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            max_range_days: Maximum allowed range in days

        Returns:
            Tuple of validated (start_time, end_time)

        Raises:
            SecurityValidationError: If time range is invalid
        """
        import datetime

        start_dt = None
        if start_time:
            try:
                start_dt = datetime.datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError:
                raise SecurityValidationError(
                    "Invalid start_time format (use ISO format)",
                    "start_time",
                    start_time,
                ) from None

        end_dt = None
        if end_time:
            try:
                end_dt = datetime.datetime.fromisoformat(
                    end_time.replace("Z", "+00:00")
                )
            except ValueError:
                raise SecurityValidationError(
                    "Invalid end_time format (use ISO format)", "end_time", end_time
                ) from None

        # Validate range
        if start_dt is not None and end_dt is not None:
            if start_dt > end_dt:
                raise SecurityValidationError(
                    "start_time must be before end_time",
                    "time_range",
                    (start_time, end_time),
                )

            range_days = (end_dt - start_dt).days
            if range_days > max_range_days:
                raise SecurityValidationError(
                    f"Time range too large (max {max_range_days} days)",
                    "time_range",
                    range_days,
                )

        return start_time, end_time


# =============================================================================
# Configuration Validation
# =============================================================================


class ConfigurationValidator:
    """Validate Harbor configuration values."""

    @staticmethod
    def validate_update_time(time_str: str) -> str:
        """Validate update time format (HH:MM)."""
        if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", time_str):
            raise SecurityValidationError(
                "Invalid time format (use HH:MM)", "update_time", time_str
            )
        return time_str

    @staticmethod
    def validate_interval_seconds(seconds: int) -> int:
        """Validate update interval."""
        if seconds < 60:  # Minimum 1 minute
            raise SecurityValidationError(
                "Interval too short (minimum 60 seconds)", "interval", seconds
            )
        if seconds > 604800:  # Maximum 1 week
            raise SecurityValidationError(
                "Interval too long (maximum 604800 seconds)", "interval", seconds
            )
        return seconds

    @staticmethod
    def validate_timezone(tz_str: str) -> str:
        """Validate timezone string."""
        # Basic timezone validation
        # TODO: Use pytz or zoneinfo for comprehensive validation
        if len(tz_str) > 50:
            raise SecurityValidationError(
                "Timezone string too long", "timezone", tz_str
            )
        if not re.match(r"^[A-Za-z/_+-]+$", tz_str):
            raise SecurityValidationError("Invalid timezone format", "timezone", tz_str)
        return tz_str


# =============================================================================
# Testing and Utilities
# =============================================================================


def test_input_sanitization() -> None:
    """Test input sanitization functions."""

    print("🧹 Testing Harbor Input Sanitization")
    print("=" * 40)

    sanitizer = InputSanitizer()

    # Test HTML sanitization
    print("1. HTML Sanitization:")
    html_tests = [
        "<script>alert('xss')</script>",
        "<img src='x' onerror='alert(1)'>",
        "Normal text with <b>bold</b>",
        "Safe text",
    ]

    for test in html_tests:
        sanitized = sanitizer.sanitize_html(test)
        print(f"   Input:  {test}")
        print(f"   Output: {sanitized}")
        print()

    # Test container name validation
    print("2. Container Name Validation:")
    name_tests = [
        "nginx-proxy",
        "valid_container-123",
        "invalid/name",  # Should fail
        "",  # Should fail
        "a" * 300,  # Should fail
    ]

    for test in name_tests:
        try:
            sanitized = sanitizer.sanitize_container_name(test)
            print(f"   ✅ '{test}' → '{sanitized}'")
        except SecurityValidationError as e:
            print(f"   ❌ '{test}' → Error: {e.message}")

    print("\n🧪 Input sanitization test complete")


if __name__ == "__main__":
    """Input validation testing and utilities"""
    test_input_sanitization()
