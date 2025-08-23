#!/usr/bin/env python3
"""
Harbor Version Validation and Changelog Generation

This script provides version validation and automated changelog generation
for Harbor Container Updater releases, following semantic versioning and
the milestone-based development approach.

Located: scripts/release/validate_version.py
Following Harbor Project Structure from foundational documents.
"""

import json
import re
import subprocess  # nosec B404  # subprocess needed for git operations
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class HarborVersionValidator:
    """Validates Harbor version consistency across project files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.app_init_path = project_root / "app" / "__init__.py"

    def get_pyproject_version(self) -> str:
        """Extract version from pyproject.toml."""
        if not self.pyproject_path.exists():
            raise FileNotFoundError(
                f"pyproject.toml not found at {self.pyproject_path}"
            )

        content = self.pyproject_path.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if not match:
            raise ValueError("Version not found in pyproject.toml")

        return match.group(1)

    def get_app_version(self) -> tuple[str, str]:
        """Extract version and milestone from app/__init__.py."""
        if not self.app_init_path.exists():
            raise FileNotFoundError(
                f"app/__init__.py not found at {self.app_init_path}"
            )

        content = self.app_init_path.read_text()

        version_match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        milestone_match = re.search(r'__milestone__\s*=\s*"([^"]+)"', content)

        if not version_match:
            raise ValueError("__version__ not found in app/__init__.py")
        if not milestone_match:
            raise ValueError("__milestone__ not found in app/__init__.py")

        return version_match.group(1), milestone_match.group(1)

    def validate_semantic_version(self, version: str) -> bool:
        """Validate semantic version format."""
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+(?:\.[0-9]+)?))?$"
        return bool(re.match(pattern, version))

    def determine_milestone_from_version(self, version: str) -> str:
        """Determine expected milestone from version number."""
        try:
            major, minor, patch = version.split("-")[0].split(".")
            version_tuple = (int(major), int(minor))

            milestone_map = {
                (0, 1): "M0",  # Foundation
                (0, 2): "M1",  # Discovery
                (0, 3): "M2",  # Updates
                (0, 4): "M3",  # Automation
                (0, 5): "M4",  # Observability
                (0, 6): "M5",  # Production
                (1, 0): "M6",  # Release
            }

            return milestone_map.get(version_tuple, "M0")
        except (ValueError, IndexError):
            return "M0"

    def validate_version_consistency(
        self, target_version: str | None = None
    ) -> dict[str, Any]:
        """Validate version consistency across all project files."""
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": {},
        }

        try:
            # Get versions from files
            pyproject_version = self.get_pyproject_version()
            app_version, app_milestone = self.get_app_version()

            result["info"]["pyproject_version"] = pyproject_version
            result["info"]["app_version"] = app_version
            result["info"]["app_milestone"] = app_milestone

            # Validate semantic version format
            if not self.validate_semantic_version(pyproject_version):
                result["errors"].append(
                    f"Invalid semantic version in pyproject.toml: {pyproject_version}"
                )
                result["valid"] = False

            if not self.validate_semantic_version(app_version):
                result["errors"].append(
                    f"Invalid semantic version in app/__init__.py: {app_version}"
                )
                result["valid"] = False

            # Check version consistency
            if pyproject_version != app_version:
                result["errors"].append(
                    f"Version mismatch: pyproject.toml ({pyproject_version}) != app/__init__.py ({app_version})"
                )
                result["valid"] = False

            # Check against target version if provided
            if target_version:
                if not self.validate_semantic_version(target_version):
                    result["errors"].append(
                        f"Invalid target version format: {target_version}"
                    )
                    result["valid"] = False

                if pyproject_version != target_version:
                    result["errors"].append(
                        f"Current version ({pyproject_version}) doesn't match target ({target_version})"
                    )
                    result["valid"] = False

            # Check milestone consistency
            expected_milestone = self.determine_milestone_from_version(
                pyproject_version
            )
            if app_milestone != expected_milestone:
                result["warnings"].append(
                    f"Milestone mismatch: app has {app_milestone}, expected {expected_milestone} for version {pyproject_version}"
                )

            result["info"]["expected_milestone"] = expected_milestone

        except Exception as e:
            result["errors"].append(f"Validation error: {e!s}")
            result["valid"] = False

        return result


class HarborChangelogGenerator:
    """Generates changelog for Harbor releases."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_git_commits_since_tag(self, since_tag: str) -> list[dict[str, str]]:
        """Get git commits since a specific tag."""
        try:
            cmd = [
                "git",
                "log",
                f"{since_tag}..HEAD",
                "--no-merges",
                "--pretty=format:%H|%s|%an|%ad",
                "--date=iso",
            ]

            # Git command is safe - using hardcoded git executable and controlled arguments
            result = subprocess.run(  # nosec B603 B607
                cmd, cwd=self.project_root, capture_output=True, text=True, check=True
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commits.append(
                            {
                                "hash": parts[0][:8],
                                "subject": parts[1],
                                "author": parts[2],
                                "date": parts[3],
                            }
                        )

            return commits

        except subprocess.CalledProcessError:
            return []

    def get_latest_tag(self) -> str | None:
        """Get the latest git tag."""
        try:
            # Git command is safe - using hardcoded git executable and controlled arguments
            result = subprocess.run(  # nosec B603 B607
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def categorize_commits(
        self, commits: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Categorize commits by type based on conventional commits."""
        categories: dict[str, list[dict[str, str]]] = {
            "features": [],
            "fixes": [],
            "docs": [],
            "chore": [],
            "breaking": [],
            "other": [],
        }

        for commit in commits:
            subject = commit["subject"].lower()

            if subject.startswith(("feat:", "feature:")):
                categories["features"].append(commit)
            elif subject.startswith(("fix:", "bugfix:")):
                categories["fixes"].append(commit)
            elif subject.startswith(("docs:", "doc:")):
                categories["docs"].append(commit)
            elif subject.startswith(("chore:", "ci:", "build:", "test:")):
                categories["chore"].append(commit)
            elif "breaking" in subject or "!" in subject:
                categories["breaking"].append(commit)
            else:
                categories["other"].append(commit)

        return categories

    def generate_changelog_content(self, version: str, milestone: str) -> str:
        """Generate changelog content for a version."""
        latest_tag = self.get_latest_tag()
        commits = self.get_git_commits_since_tag(latest_tag) if latest_tag else []
        categorized = self.categorize_commits(commits)

        # Get unique contributors - FIXED: Using set comprehension instead of generator
        contributors = sorted({commit["author"] for commit in commits})

        # Generate changelog
        changelog = f"""# Harbor Container Updater {version}

**Milestone**: {milestone}
**Release Date**: {datetime.utcnow().strftime("%Y-%m-%d")}
**Release Type**: {"Pre-release" if any(x in version for x in ["alpha", "beta", "rc"]) else "Stable Release"}

## 🎯 Milestone Progress

Harbor follows a structured development roadmap with clear milestones:

- **M0 (Foundation)**: Project infrastructure, CI/CD, basic app structure {"✅" if milestone == "M0" else "🚧" if milestone == "M1" else "📋"}
- **M1 (Discovery)**: Container discovery and registry integration {"✅" if milestone in ["M1", "M2", "M3", "M4", "M5", "M6"] else "🚧" if milestone == "M1" else "📋"}
- **M2 (Updates)**: Safe update engine with rollback capability {"✅" if milestone in ["M2", "M3", "M4", "M5", "M6"] else "🚧" if milestone == "M2" else "📋"}
- **M3 (Automation)**: Scheduling and web interface {"✅" if milestone in ["M3", "M4", "M5", "M6"] else "🚧" if milestone == "M3" else "📋"}
- **M4 (Observability)**: Monitoring and metrics {"✅" if milestone in ["M4", "M5", "M6"] else "🚧" if milestone == "M4" else "📋"}
- **M5 (Production)**: Security hardening and performance {"✅" if milestone in ["M5", "M6"] else "🚧" if milestone == "M5" else "📋"}
- **M6 (Release)**: Community launch and documentation {"✅" if milestone == "M6" else "🚧" if milestone == "M6" else "📋"}

Current status: **{milestone} Phase**

## 📦 Installation

### Quick Start (30 seconds)
```bash
docker run -d --name harbor --restart unless-stopped \\
  -p 8080:8080 \\
  -v /var/run/docker.sock:/var/run/docker.sock:ro \\
  -v harbor-data:/app/data \\
  ghcr.io/deusextaco/harbor:{version}
```

### Docker Compose
```yaml
version: '3.8'
services:
  harbor:
    image: ghcr.io/deusextaco/harbor:{version}
    container_name: harbor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - harbor_data:/app/data
    environment:
      - HARBOR_MODE=homelab
    labels:
      - "harbor.exclude=true"

volumes:
  harbor_data:
```

"""

        # Add changes section if we have commits
        if commits:
            changelog += f"## 🌟 What's New in {version}\n\n"

            if latest_tag:
                changelog += f"### 📄 Changes Since {latest_tag}\n\n"
            else:
                changelog += "### 🎉 Initial Release Features\n\n"

            # Add categorized changes
            if categorized["breaking"]:
                changelog += "#### 💥 Breaking Changes\n"
                for commit in categorized["breaking"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            if categorized["features"]:
                changelog += "#### ✨ New Features\n"
                for commit in categorized["features"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            if categorized["fixes"]:
                changelog += "#### 🐛 Bug Fixes\n"
                for commit in categorized["fixes"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            if categorized["docs"]:
                changelog += "#### 📚 Documentation\n"
                for commit in categorized["docs"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            if categorized["chore"]:
                changelog += "#### 🔧 Maintenance\n"
                for commit in categorized["chore"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            if categorized["other"]:
                changelog += "#### 📄 Other Changes\n"
                for commit in categorized["other"]:
                    changelog += f"- {commit['subject']} ({commit['hash']})\n"
                changelog += "\n"

            # Add contributors
            if contributors:
                changelog += "### 👥 Contributors\n\n"
                for contributor in contributors:
                    changelog += f"- {contributor}\n"
                changelog += "\n"

        else:
            # Initial release content
            changelog += """### 🎉 Initial Release Features

- ✅ FastAPI-based web framework with automatic OpenAPI documentation
- ✅ Zero-configuration deployment for home labs
- ✅ SQLite database with automatic migrations
- ✅ Profile-based configuration (homelab, development, production)
- ✅ Comprehensive health checks and monitoring endpoints
- ✅ Docker container health checking
- ✅ Complete CI/CD pipeline with multi-stage testing
- ✅ Security scanning and vulnerability detection
- ✅ Multi-architecture Docker images (amd64 ready, arm64/armv7 planned)
- ✅ Development environment with hot reload
- ✅ Comprehensive test suite with unit and integration tests

### 🗗️ Foundation Complete

This release completes the M0 (Foundation) milestone, establishing:
- Solid project structure following open-source best practices
- Comprehensive CI/CD pipeline with automated testing and security scanning
- Development-friendly tooling and documentation
- Production-ready Docker images and deployment configurations
- Extensible architecture ready for M1 feature development

"""

        # Add footer
        changelog += """## 🚀 Getting Started

1. **Quick Setup**: Use the Docker command above for instant deployment
2. **Dashboard**: Visit http://localhost:8080 after startup
3. **Documentation**: Full documentation at https://harbor-docs.dev
4. **Support**: GitHub Issues for bug reports and feature requests

## 🛣️ What's Next

### M1 Milestone (Container Discovery & Registry Integration)
- Automatic container discovery with change detection
- Multi-registry support (Docker Hub, GHCR, private registries)
- Intelligent caching and rate limiting
- Container specification analysis and tracking

### Future Milestones
- **M2**: Safe update engine with health checks and rollback
- **M3**: Scheduling system and comprehensive web interface
- **M4**: Monitoring, metrics, and alerting
- **M5**: Production hardening and enterprise features
- **M6**: Community launch and ecosystem integration

## 📊 Technical Details

- **Supported Platforms**: linux/amd64 (arm64/armv7 coming in M1)
- **Python Version**: 3.11+ (tested on 3.11, 3.12, 3.13)
- **Database**: SQLite (PostgreSQL support in M7+)
- **Web Framework**: FastAPI with uvicorn
- **Container Runtime**: Docker (Kubernetes/Podman planned)

---

"""

        if latest_tag:
            changelog += f"**Full Changelog**: https://github.com/DeusExTaco/harbor/compare/{latest_tag}...v{version}\n"
        else:
            changelog += "**Repository**: https://github.com/DeusExTaco/harbor\n"

        return changelog


def main() -> int:
    """Main CLI function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harbor Version Validation and Changelog Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_version.py validate
  python validate_version.py validate --target 0.1.1
  python validate_version.py changelog --version 0.1.1 --milestone M0
  python validate_version.py changelog --version 0.1.1 --output CHANGELOG.md

This script is part of Harbor's release automation system.
It follows the project structure defined in the foundational documents.
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate version consistency"
    )
    validate_parser.add_argument("--target", help="Target version to validate against")
    validate_parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    # Changelog command
    changelog_parser = subparsers.add_parser("changelog", help="Generate changelog")
    changelog_parser.add_argument(
        "--version", required=True, help="Version for changelog generation"
    )
    changelog_parser.add_argument(
        "--milestone", help="Milestone for the release (auto-detected if not specified)"
    )
    changelog_parser.add_argument(
        "--output", help="Output file (stdout if not specified)"
    )
    changelog_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    if not (project_root / "pyproject.toml").exists():
        print("❌ Error: Could not find project root (pyproject.toml not found)")
        print(f"   Searched in: {project_root}")
        return 1

    if args.command == "validate":
        validator = HarborVersionValidator(project_root)
        result = validator.validate_version_consistency(args.target)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("🔍 Harbor Version Validation")
            print("=" * 30)

            if result["valid"]:
                print("✅ All validation checks passed!")
            else:
                print("❌ Validation failed!")

            print("📦 Project Information:")
            for key, value in result["info"].items():
                print(f"   {key}: {value}")

            if result["errors"]:
                print("❌ Errors:")
                for error in result["errors"]:
                    print(f"   • {error}")

            if result["warnings"]:
                print("⚠️  Warnings:")
                for warning in result["warnings"]:
                    print(f"   • {warning}")

        return 0 if result["valid"] else 1

    elif args.command == "changelog":
        generator = HarborChangelogGenerator(project_root)
        validator = HarborVersionValidator(project_root)

        # Validate version format
        if not validator.validate_semantic_version(args.version):
            print(f"❌ Error: Invalid version format: {args.version}")
            print("   Expected format: X.Y.Z or X.Y.Z-prerelease")
            return 1

        # Determine milestone if not provided
        milestone = args.milestone
        if not milestone:
            milestone = validator.determine_milestone_from_version(args.version)

        # Generate changelog
        if args.format == "json":
            # Generate structured data for JSON
            latest_tag = generator.get_latest_tag()
            commits = (
                generator.get_git_commits_since_tag(latest_tag) if latest_tag else []
            )
            categorized = generator.categorize_commits(commits)
            # FIXED: Using set comprehension instead of generator
            contributors = sorted({commit["author"] for commit in commits})

            changelog_data = {
                "version": args.version,
                "milestone": milestone,
                "release_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "previous_tag": latest_tag,
                "commits": {
                    "total": len(commits),
                    "by_category": {k: len(v) for k, v in categorized.items()},
                    "details": categorized,
                },
                "contributors": contributors,
            }

            changelog_content = json.dumps(changelog_data, indent=2)
        else:
            changelog_content = generator.generate_changelog_content(
                args.version, milestone
            )

        # Output changelog
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(changelog_content)
            print(f"✅ Changelog written to: {output_path}")
        else:
            print(changelog_content)

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
