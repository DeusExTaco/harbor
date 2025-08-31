#!/usr/bin/env python3
"""
Manual testing script for API Key Management
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["HARBOR_MODE"] = "development"

from app.auth.api_keys import APIKeyManager


async def main():
    """Test API key functionality manually"""
    print("=" * 60)
    print("HARBOR API KEY TESTING")
    print("=" * 60)

    manager = APIKeyManager()

    print("\n1. Generating API Keys")
    print("-" * 40)

    for i in range(3):
        plain_key, hashed_key = manager.generate_api_key()
        print(f"Key {i + 1}:")
        print(f"  Plain:  {plain_key}")
        print(f"  Hash:   {hashed_key[:32]}...")
        print(f"  Valid:  {manager.validate_api_key_format(plain_key)}")

    print("\n2. Testing Validation")
    print("-" * 40)

    test_keys = [
        ("Valid key", "sk_harbor_abcd1234efgh5678"),
        ("Empty", ""),
        ("Wrong prefix", "wrong_prefix_key"),
        ("Too short", "sk_harbor_"),
        ("Invalid chars", "sk_harbor_!@#$%^&*"),
    ]

    for desc, key in test_keys:
        valid = manager.validate_api_key_format(key)
        print(f"{desc:15} | {key[:30]:30} | {'✓' if valid else '✗'}")

    print("\n3. Testing Verification")
    print("-" * 40)

    plain_key, hashed_key = manager.generate_api_key()

    tests = [
        ("Correct key", plain_key, hashed_key, True),
        ("Wrong key", "sk_harbor_wrongkey", hashed_key, False),
        ("Wrong hash", plain_key, "wronghash", False),
    ]

    for desc, key, hash_val, expected in tests:
        result = manager.verify_api_key(key, hash_val)
        status = "✓" if result == expected else "✗"
        print(f"{desc:15} | Expected: {expected} | Got: {result} | {status}")

    print("\n✅ Manual testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
