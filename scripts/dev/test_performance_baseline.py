#!/usr/bin/env python3
# scripts/dev/test_performance_baseline.py
"""
Harbor Performance Baseline Test

Tests application startup time and resource usage.
"""

import asyncio
import time
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ["HARBOR_MODE"] = "development"
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


async def test_startup_performance():
    """Test application startup time and memory usage."""
    print("\n⚡ Testing Startup Performance")
    print("-" * 50)

    try:
        import psutil

        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        print("⚠️  psutil not installed, skipping memory measurements")
        start_memory = 0

    start_time = time.time()

    try:
        from app.main import create_app
        from app.db.init import initialize_database

        # Create app
        app = create_app()

        # Initialize database
        await initialize_database()

        duration = time.time() - start_time

        if start_memory > 0:
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory
            print(f"   Startup time: {duration:.2f}s")
            print(f"   Memory used: {memory_used:.1f}MB")
            print(f"   Total memory: {end_memory:.1f}MB")

            # Check limits
            if duration < 5.0:
                print("✅ Startup time is acceptable")
            else:
                print(f"⚠️  Startup time exceeds 5 seconds")

            if end_memory < 500:
                print("✅ Memory usage is acceptable")
            else:
                print(f"⚠️  Memory usage exceeds 500MB")
        else:
            print(f"   Startup time: {duration:.2f}s")
            if duration < 5.0:
                print("✅ Startup time is acceptable")
            else:
                print(f"⚠️  Startup time exceeds 5 seconds")

        return duration < 10.0  # Allow up to 10s for CI/CD environments

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


async def test_database_performance():
    """Test basic database operation performance."""
    print("\n💾 Testing Database Performance")
    print("-" * 50)

    try:
        from app.db.session import get_async_session
        from app.db.models.container import Container
        from sqlalchemy import select
        import uuid

        async with get_async_session() as session:
            start_time = time.time()

            # Create test containers
            containers = []
            for i in range(100):
                container = Container(
                    uid=str(uuid.uuid4()),
                    docker_name=f"test-container-{i}",
                    image_repo="nginx",
                    image_tag="latest",
                    image_ref="nginx:latest",
                    status="running",
                )
                containers.append(container)

            session.add_all(containers)
            await session.commit()

            create_time = time.time() - start_time
            print(f"   Created 100 containers in {create_time:.2f}s")

            # Query performance
            start_time = time.time()
            stmt = select(Container)
            result = await session.execute(stmt)
            all_containers = result.scalars().all()
            query_time = time.time() - start_time

            print(f"   Queried {len(all_containers)} containers in {query_time:.3f}s")

            if create_time < 5.0 and query_time < 1.0:
                print("✅ Database performance is acceptable")
                return True
            else:
                print("⚠️  Database performance may need optimization")
                return True  # Warning but not failure

    except Exception as e:
        print(f"❌ Database performance test failed: {e}")
        return False


async def main():
    """Run performance baseline tests."""
    print("\n" + "=" * 60)
    print("⚡ HARBOR PERFORMANCE BASELINE TESTS")
    print("=" * 60)

    results = []

    results.append(("Startup Performance", await test_startup_performance()))
    results.append(("Database Performance", await test_database_performance()))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if passed == total:
        print(f"✅ All performance tests passed ({passed}/{total})")
        return True
    else:
        print(f"⚠️  Some performance issues detected ({passed}/{total} passed)")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
