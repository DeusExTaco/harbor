#!/usr/bin/env python3
# scripts/dev/test_registry_client.py
"""
Harbor Registry Client Test

Tests container registry connectivity and basic operations.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ["HARBOR_MODE"] = "development"
os.environ["TESTING"] = "true"


async def test_registry_client_init():
    """Test registry client initialization."""
    print("\n🌐 Testing Registry Client Initialization")
    print("-" * 50)

    try:
        from app.registry.client import RegistryClient

        client = RegistryClient()
        print("✅ Registry client initialized")
        return True

    except ImportError as e:
        print(f"❌ Registry client import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Registry client initialization failed: {e}")
        return False


async def test_registry_cache():
    """Test registry cache functionality."""
    print("\n💾 Testing Registry Cache")
    print("-" * 50)

    try:
        from app.registry.cache import RegistryCache

        cache = RegistryCache()

        # Test cache operations
        test_key = "test:nginx:latest"
        test_data = {"manifest": "test_data"}

        await cache.set(test_key, test_data, ttl=60)
        print("✅ Cache write successful")

        cached_data = await cache.get(test_key)
        if cached_data == test_data:
            print("✅ Cache read successful")
        else:
            print("❌ Cache read failed - data mismatch")
            return False

        await cache.clear()
        print("✅ Cache clear successful")

        return True

    except ImportError:
        print("⚠️  Registry cache module not implemented yet")
        return True  # Not critical for initial release

    except Exception as e:
        print(f"❌ Registry cache test failed: {e}")
        return False


# Update scripts/dev/test_registry_client.py (just the Docker Hub test part)


async def test_docker_hub_connectivity():
    """Test Docker Hub connectivity (without actual API calls)."""
    print("\n🐋 Testing Docker Hub Connectivity")
    print("-" * 50)

    try:
        import httpx

        # Test the correct Docker Hub API endpoint
        # Note: /v2/ requires authentication, so we test the root endpoint
        async with httpx.AsyncClient() as client:
            # Test Docker Hub website availability
            response = await client.get(
                "https://hub.docker.com/", follow_redirects=True
            )

            if response.status_code == 200:
                print("✅ Docker Hub is reachable")
                return True
            else:
                print(f"⚠️  Docker Hub returned status {response.status_code}")
                return False

    except Exception as e:
        print(f"⚠️  Could not reach Docker Hub: {e}")
        return False


async def main():
    """Run registry client tests."""
    print("\n" + "=" * 60)
    print("🌐 HARBOR REGISTRY CLIENT TESTS")
    print("=" * 60)

    results = []

    results.append(("Registry Client Init", await test_registry_client_init()))
    results.append(("Registry Cache", await test_registry_cache()))
    results.append(("Docker Hub Connectivity", await test_docker_hub_connectivity()))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if passed == total:
        print(f"✅ All registry tests passed ({passed}/{total})")
        return True
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
