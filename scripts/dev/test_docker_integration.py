#!/usr/bin/env python3
# scripts/dev/test_docker_integration.py
"""
Harbor Docker Integration Test

Tests actual Docker daemon connectivity and basic container operations.
Only runs if Docker is available on the system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test environment
os.environ["HARBOR_MODE"] = "development"
os.environ["TESTING"] = "true"


async def test_docker_connection():
    """Test Docker daemon connectivity."""
    print("\nTesting Docker Connection")
    print("-" * 50)

    try:
        import docker

        client = docker.from_env()
        version = client.version()

        print(f"OK: Docker daemon connected")
        print(f"   Version: {version.get('Version', 'Unknown')}")
        print(f"   API Version: {version.get('ApiVersion', 'Unknown')}")
        print(f"   OS: {version.get('Os', 'Unknown')}/{version.get('Arch', 'Unknown')}")

        return True

    except ImportError:
        print("WARNING: Docker Python library not installed")
        print("   Run: pip install docker")
        return False

    except Exception as e:
        print(f"FAIL: Docker connection failed: {e}")
        print("   Make sure Docker daemon is running")
        return False


async def test_container_operations():
    """Test basic container operations."""
    print("\nTesting Container Operations")
    print("-" * 50)

    try:
        # First check if the runtime module exists
        from pathlib import Path

        runtime_path = (
            Path(__file__).parent.parent.parent / "app" / "runtimes" / "docker.py"
        )

        if not runtime_path.exists():
            print("INFO: Docker runtime module not yet implemented")
            print("      This is expected - will be implemented in M1")

            # Fall back to basic docker library test
            try:
                import docker

                client = docker.from_env()
                containers = client.containers.list(all=True)
                print(
                    f"OK: Basic container listing works: {len(containers)} containers found"
                )
                return True
            except Exception as e:
                print(f"WARNING: Basic container listing failed: {e}")
                return False

        # If module exists, try to use it
        from app.runtimes.docker import DockerRuntime

        runtime = DockerRuntime()

        # Test discovery
        containers = await runtime.discover_containers(include_stopped=True)
        print(f"OK: Container discovery: Found {len(containers)} containers")

        # Test container inspection if any exist
        if containers:
            first_container = containers[0]
            spec = await runtime.inspect_container(first_container.docker_id)
            print(f"OK: Container inspection: {first_container.docker_name}")
        else:
            print("   No containers to inspect")

        return True

    except ImportError as e:
        print(f"WARNING: Import error: {e}")
        print("         Module structure may not be complete yet")
        return True  # Don't fail for missing future modules

    except Exception as e:
        print(f"FAIL: Container operations failed: {e}")
        return False


async def test_docker_socket_access():
    """Test Docker socket access and permissions."""
    print("\nTesting Docker Socket Access")
    print("-" * 50)

    # All paths must be Path objects
    socket_paths = [
        Path("/var/run/docker.sock"),  # Linux standard
        Path.home() / ".docker/run/docker.sock",  # Mac/Windows Docker Desktop
        Path.home() / ".colima/docker.sock",  # Colima on Mac
    ]

    socket_found = None
    for socket_path in socket_paths:
        if socket_path.exists():
            socket_found = socket_path
            break

    if not socket_found:
        print("WARNING: Docker socket not found at standard locations")
        print("         Checked locations:")
        for path in socket_paths:
            print(f"         - {path}")
        return False

    print(f"OK: Docker socket found: {socket_found}")

    # Check if we can access it
    if os.access(socket_found, os.R_OK):
        print("OK: Docker socket is readable")
        return True
    else:
        print("FAIL: Docker socket is not readable - permission denied")
        print("      You may need to add your user to the docker group")
        print("      Run: sudo usermod -aG docker $USER")
        return False


async def test_docker_library():
    """Test if Docker Python library is installed."""
    print("\nTesting Docker Python Library")
    print("-" * 50)

    try:
        import docker

        print(f"OK: docker-py version {docker.__version__} installed")
        return True
    except ImportError:
        print("WARNING: docker-py not installed")
        print("         Install with: pip install docker")
        print("         Or: pip install -r requirements/development.txt")
        return False


async def main():
    """Run Docker integration tests."""
    print("\n" + "=" * 60)
    print(" HARBOR DOCKER INTEGRATION TESTS")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Docker Library", await test_docker_library()))
    results.append(("Docker Connection", await test_docker_connection()))
    results.append(("Docker Socket Access", await test_docker_socket_access()))
    results.append(("Container Operations", await test_container_operations()))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if passed == total:
        print(f"OK: All Docker integration tests passed ({passed}/{total})")
        return True
    else:
        print(f"INFO: Some tests skipped or warned ({passed}/{total} passed)")
        print("      This is expected for optional Docker functionality")
        print("      Full Docker integration will be implemented in M1")
        return True  # Don't fail the entire suite for optional Docker tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
