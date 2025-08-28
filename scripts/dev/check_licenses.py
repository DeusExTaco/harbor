# scripts/dev/check_licenses.py
"""
Enhanced License Compliance Checker

Checks package licenses with fallback to PyPI metadata and manual overrides.
"""

import json
import subprocess
import sys
from pathlib import Path

import requests


# Known license overrides for packages that report "UNKNOWN"
# Verified from PyPI and official repositories
LICENSE_OVERRIDES = {
    # Original overrides
    "Markdown": "BSD-3-Clause",
    "alembic": "MIT",
    "anyio": "MIT",
    "argon2-cffi-bindings": "MIT",
    "click": "BSD-3-Clause",
    "licensecheck": "MIT",
    "prometheus_client": "Apache-2.0",
    "prometheus-client": "Apache-2.0",
    "typing-inspection": "MIT",
    "typing_extensions": "PSF-2.0",
    "typing-extensions": "PSF-2.0",
    "urllib3": "MIT",
    # Additional packages with UNKNOWN licenses (verified from PyPI)
    "CacheControl": "Apache-2.0",
    "Flask": "BSD-3-Clause",
    "attrs": "MIT",
    "jsonschema": "MIT",
    "jsonschema-specifications": "MIT",
    "jupyter_core": "BSD-3-Clause",
    "mypy_extensions": "MIT",
    "playwright": "Apache-2.0",
    "pytest-xdist": "MIT",
    "pyyaml_env_tag": "MIT",
    "referencing": "MIT",
    "rpds-py": "MIT",
    "types-PyYAML": "Apache-2.0",
    "types-psutil": "Apache-2.0",
    "types-python-dateutil": "Apache-2.0",
    "types-requests": "Apache-2.0",
}

# Allowed licenses for Harbor project
ALLOWED_LICENSES = {
    "MIT",
    "MIT License",
    "Apache-2.0",
    "Apache Software License",
    "Apache License 2.0",
    "Apache 2.0",
    "BSD",
    "BSD License",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "ISC License",
    "ISCL",
    "PSF-2.0",
    "Python Software Foundation License",
    "Python-2.0",
    "0BSD",
    "Unlicense",
    "The Unlicense",
    # Add MPL as conditionally allowed for specific packages
    "MPL-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)",
}

# Packages that are acceptable even with restrictive licenses
# These are typically build/test dependencies, not runtime
ACCEPTABLE_EXCEPTIONS = {
    "psycopg2-binary": "Development/test only - not in production image",
    "certifi": "Standard certificate bundle - MPL is acceptable",
    "pathspec": "Build tool dependency only",
    "pytest-metadata": "Test dependency only",
    "fqdn": "Optional validation library",
}


def get_pypi_license(package_name: str) -> str | None:
    """
    Fetch license information from PyPI API.
    """
    try:
        # Try exact package name first
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            info = data.get("info", {})
            license_str = info.get("license", "")
            if license_str and license_str != "UNKNOWN":
                return license_str

            # Check classifiers for license info
            classifiers = info.get("classifiers", [])
            for classifier in classifiers:
                if "License ::" in classifier:
                    # Extract license from classifier
                    parts = classifier.split("::")
                    if len(parts) > 1:
                        license_name = parts[-1].strip()
                        return license_name

        # Try with underscores replaced by hyphens
        alt_name = package_name.replace("_", "-")
        if alt_name != package_name:
            response = requests.get(f"https://pypi.org/pypi/{alt_name}/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                license_str = data.get("info", {}).get("license", "")
                if license_str and license_str != "UNKNOWN":
                    return license_str

    except Exception as e:
        print(f"  Could not fetch PyPI data for {package_name}: {e}")

    return None


def check_license_compliance():
    """
    Check license compliance with enhanced detection.
    """
    print("📋 Enhanced License Compliance Check")
    print("-" * 50)

    # Get installed packages with pip-licenses
    try:
        result = subprocess.run(
            ["pip-licenses", "--format=json", "--with-urls"],
            capture_output=True,
            text=True,
            check=True,
        )
        packages = json.loads(result.stdout)
    except Exception as e:
        print(f"❌ Failed to get package licenses: {e}")
        return False

    # Analyze licenses
    unknown_licenses = []
    problematic_licenses = []
    fixed_licenses = []
    acceptable_exceptions_found = []

    for package in packages:
        name = package.get("Name", "")
        version = package.get("Version", "")
        license_str = package.get("License", "UNKNOWN")

        # Check if license is unknown
        if license_str in ["UNKNOWN", "", None]:
            # Try to get from overrides
            if name in LICENSE_OVERRIDES:
                fixed_license = LICENSE_OVERRIDES[name]
                fixed_licenses.append(
                    {
                        "name": name,
                        "version": version,
                        "original": "UNKNOWN",
                        "fixed": fixed_license,
                    }
                )
                license_str = fixed_license
            else:
                # Try to fetch from PyPI
                pypi_license = get_pypi_license(name)
                if pypi_license:
                    fixed_licenses.append(
                        {
                            "name": name,
                            "version": version,
                            "original": "UNKNOWN",
                            "fixed": pypi_license,
                        }
                    )
                    license_str = pypi_license
                else:
                    unknown_licenses.append({"name": name, "version": version})
                    continue

        # Check if this is an acceptable exception
        if name in ACCEPTABLE_EXCEPTIONS:
            acceptable_exceptions_found.append(
                {
                    "name": name,
                    "version": version,
                    "license": license_str,
                    "reason": ACCEPTABLE_EXCEPTIONS[name],
                }
            )
            continue

        # Check if license is allowed
        license_normalized = license_str.strip()
        is_allowed = False

        for allowed in ALLOWED_LICENSES:
            if allowed.lower() in license_normalized.lower():
                is_allowed = True
                break

        # Special case for multi-license packages
        if " OR " in license_normalized or " AND " in license_normalized:
            # Check if any part is allowed
            parts = (
                license_normalized.replace(" OR ", ";").replace(" AND ", ";").split(";")
            )
            for part in parts:
                for allowed in ALLOWED_LICENSES:
                    if allowed.lower() in part.lower():
                        is_allowed = True
                        break

        if not is_allowed and license_str != "UNKNOWN":
            # Check if it's LGPL and is psycopg2-binary (special case)
            if "LGPL" in license_str and name == "psycopg2-binary":
                acceptable_exceptions_found.append(
                    {
                        "name": name,
                        "version": version,
                        "license": license_str,
                        "reason": "Test/dev dependency only",
                    }
                )
            else:
                problematic_licenses.append(
                    {"name": name, "version": version, "license": license_str}
                )

    # Report results
    print("\n📊 License Analysis Results:")
    print(f"  Total packages: {len(packages)}")
    print(f"  Fixed licenses: {len(fixed_licenses)}")
    print(f"  Unknown licenses: {len(unknown_licenses)}")
    print(f"  Problematic licenses: {len(problematic_licenses)}")
    print(f"  Acceptable exceptions: {len(acceptable_exceptions_found)}")

    if fixed_licenses:
        print("\n✅ Fixed License Mappings:")
        for fix in fixed_licenses:
            print(
                f"  {fix['name']} ({fix['version']}): {fix['original']} → {fix['fixed']}"
            )

    if acceptable_exceptions_found:
        print("\n✅ Acceptable Exceptions:")
        for exc in acceptable_exceptions_found:
            print(f"  {exc['name']} ({exc['version']}): {exc['license']}")
            print(f"    Reason: {exc['reason']}")

    if unknown_licenses:
        print("\n⚠️ Still Unknown Licenses:")
        for pkg in unknown_licenses:
            print(f"  {pkg['name']} ({pkg['version']})")

    if problematic_licenses:
        print("\n❌ Problematic Licenses:")
        for pkg in problematic_licenses:
            print(f"  {pkg['name']} ({pkg['version']}): {pkg['license']}")

    # Write override configuration
    write_license_config(fixed_licenses, acceptable_exceptions_found)

    # Determine pass/fail
    if len(unknown_licenses) == 0 and len(problematic_licenses) == 0:
        print("\n✅ License compliance check passed!")
        return True
    else:
        print("\n⚠️ License compliance needs review")
        print("\nTo fix remaining issues:")
        print("1. Add more overrides to LICENSE_OVERRIDES")
        print("2. Add exceptions to ACCEPTABLE_EXCEPTIONS")
        print("3. Consider removing problematic dependencies")
        return False


def write_license_config(fixed_licenses, exceptions):
    """
    Write license configuration for CI/CD.
    """
    config = {
        "license_overrides": LICENSE_OVERRIDES,
        "fixed_from_pypi": {
            fix["name"]: fix["fixed"]
            for fix in fixed_licenses
            if fix["name"] not in LICENSE_OVERRIDES
        },
        "acceptable_exceptions": ACCEPTABLE_EXCEPTIONS,
    }

    config_path = Path(".github/license-overrides.json")
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n💾 License configuration saved to {config_path}")


if __name__ == "__main__":
    success = check_license_compliance()
    sys.exit(0 if success else 1)
