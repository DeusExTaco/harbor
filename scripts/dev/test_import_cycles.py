#!/usr/bin/env python3
# scripts/dev/test_import_cycles.py
"""
Harbor Import Cycle Detection

Checks for circular imports in the codebase.
"""

import sys
import importlib
import traceback
from pathlib import Path


def test_module_imports():
    """Test that all major modules can be imported without cycles."""
    print("\n🔄 Testing for Import Cycles")
    print("-" * 50)

    # Add app to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    modules_to_check = [
        "app",
        "app.main",
        "app.config",
        "app.db.base",
        "app.db.session",
        "app.db.init",
        "app.auth.manager",
        "app.auth.api_keys",
        "app.auth.sessions",
        "app.security",
        "app.security.headers",
        "app.security.rate_limit",
        "app.services.discovery",
        "app.services.updater",
        "app.services.health",
    ]

    failed = []

    for module_name in modules_to_check:
        try:
            importlib.import_module(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            if "No module named" in str(e) and "services" in module_name:
                print(f"⚠️  {module_name}: Not implemented yet")
            else:
                print(f"❌ {module_name}: {e}")
                failed.append((module_name, str(e)))
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            failed.append((module_name, str(e)))

    if failed:
        print("\n❌ Import failures detected:")
        for module, error in failed:
            print(f"   {module}: {error}")
        return False
    else:
        print("\n✅ No import cycles detected")
        return True


def main():
    """Run import cycle detection."""
    print("\n" + "=" * 60)
    print("🔄 HARBOR IMPORT CYCLE DETECTION")
    print("=" * 60)

    success = test_module_imports()

    if success:
        print("\n✅ All modules import successfully")
    else:
        print("\n❌ Import issues detected")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
