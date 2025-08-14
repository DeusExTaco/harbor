#!/usr/bin/env python3
"""
Harbor Container Health Check Script

This script is used by Docker's HEALTHCHECK instruction to verify
that the Harbor application is running correctly inside a container.

Exit codes:
- 0: Healthy
- 1: Unhealthy
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def check_health() -> dict[str, Any]:
    """
    Check Harbor application health.

    Returns:
        Dict containing health status and details
    """
    port = os.getenv("HARBOR_PORT", "8080")
    # Static localhost URL - safe for bandit security check
    health_url = f"http://localhost:{port}/healthz"  # nosec B310

    try:
        # Create request with timeout
        request = urllib.request.Request(health_url)
        request.add_header("User-Agent", "Harbor-HealthCheck/1.0")

        # Make health check request - static URL, no user input
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310
            if response.status == 200:
                try:
                    data = json.loads(response.read().decode())
                    return {
                        "status": "healthy",
                        "http_status": response.status,
                        "response": data,
                    }
                except json.JSONDecodeError:
                    # If response isn't JSON, just check HTTP status
                    return {
                        "status": "healthy",
                        "http_status": response.status,
                        "response": "OK",
                    }
            else:
                return {
                    "status": "unhealthy",
                    "http_status": response.status,
                    "error": f"HTTP {response.status}",
                }

    except urllib.error.HTTPError as e:
        return {
            "status": "unhealthy",
            "error": f"HTTP {e.code}: {e.reason}",
            "url": health_url,
        }
    except urllib.error.URLError as e:
        return {
            "status": "unhealthy",
            "error": f"Connection failed: {e.reason}",
            "url": health_url,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": f"Health check failed: {e!s}",
            "url": health_url,
        }


def main() -> int:
    """Main health check function."""
    try:
        result = check_health()

        if result["status"] == "healthy":
            print("✅ Harbor is healthy")
            if "response" in result and isinstance(result["response"], dict):
                print(f"   Status: {result['response'].get('status', 'OK')}")
                print(f"   Version: {result['response'].get('version', 'unknown')}")
            return 0
        else:
            print("❌ Harbor is unhealthy")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Health check script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
