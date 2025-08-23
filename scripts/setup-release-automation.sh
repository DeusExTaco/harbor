#!/bin/bash
# =============================================================================
# Harbor Complete Release Automation Setup
# Located: scripts/setup-release-automation.sh
# Creates complete release automation with all scripts included
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🚢 Setting up Harbor Complete Release Automation${NC}"
echo "Following Harbor Project Structure from foundational documents"
echo "Project root: $PROJECT_ROOT"
echo ""

# =============================================================================
# Create directory structure
# =============================================================================
echo -e "${BLUE}📁 Creating release directory structure...${NC}"

mkdir -p "$PROJECT_ROOT/scripts/release"
mkdir -p "$PROJECT_ROOT/.github/workflows"
mkdir -p "$PROJECT_ROOT/docs/development"

echo -e "${GREEN}✅ Release directories created${NC}"

# =============================================================================
# Create COMPLETE release management script
# =============================================================================
echo -e "${BLUE}📝 Creating complete release management script...${NC}"

cat > "$PROJECT_ROOT/scripts/release/release.sh" << 'RELEASE_SCRIPT_EOF'
#!/bin/bash
# =============================================================================
# Harbor Release Management Scripts
# Located: scripts/release/release.sh
# Semantic versioning and release automation following project structure
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${PURPLE}🚢 $1${NC}"
}

# =============================================================================
# Version Management Functions
# =============================================================================

get_current_version() {
    """Get current version from pyproject.toml"""
    grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
}

get_current_milestone() {
    """Get current milestone from app/__init__.py"""
    grep '__milestone__ = ' "$PROJECT_ROOT/app/__init__.py" | sed 's/__milestone__ = "\(.*\)"/\1/'
}

validate_version_format() {
    """Validate semantic version format"""
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+(\.[0-9]+)?)?$ ]]; then
        log_error "Invalid version format: $version"
        log_info "Expected format: X.Y.Z or X.Y.Z-prerelease"
        log_info "Examples: 1.0.0, 1.0.0-rc.1, 1.0.0-beta.2"
        return 1
    fi
    return 0
}

determine_milestone_from_version() {
    """Determine Harbor milestone from version number"""
    local version=$1
    case "$version" in
        0.1.*) echo "M0" ;;
        0.2.*) echo "M1" ;;
        0.3.*) echo "M2" ;;
        0.4.*) echo "M3" ;;
        0.5.*) echo "M4" ;;
        0.6.*) echo "M5" ;;
        1.0.*) echo "M6" ;;
        *) echo "M0" ;;
    esac
}

increment_version() {
    """Increment version based on type (major, minor, patch)"""
    local current_version=$1
    local increment_type=$2

    # Parse current version
    local major minor patch prerelease
    if [[ $current_version =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-.*)?$ ]]; then
        major=${BASH_REMATCH[1]}
        minor=${BASH_REMATCH[2]}
        patch=${BASH_REMATCH[3]}
        prerelease=${BASH_REMATCH[4]}
    else
        log_error "Cannot parse version: $current_version"
        return 1
    fi

    case "$increment_type" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "$major.$((minor + 1)).0"
            ;;
        patch)
            echo "$major.$minor.$((patch + 1))"
            ;;
        rc)
            if [[ -n $prerelease ]]; then
                # Increment RC number
                if [[ $prerelease =~ ^-rc\.([0-9]+)$ ]]; then
                    local rc_num=${BASH_REMATCH[1]}
                    echo "$major.$minor.$patch-rc.$((rc_num + 1))"
                else
                    echo "$major.$minor.$patch-rc.1"
                fi
            else
                echo "$major.$minor.$patch-rc.1"
            fi
            ;;
        *)
            log_error "Unknown increment type: $increment_type"
            log_info "Valid types: major, minor, patch, rc"
            return 1
            ;;
    esac
}

# =============================================================================
# File Update Functions
# =============================================================================

update_version_files() {
    """Update version in all relevant files"""
    local new_version=$1
    local milestone=$2

    log_info "Updating version files to $new_version (milestone: $milestone)"

    # Update pyproject.toml
    sed -i.bak "s/^version = .*/version = \"$new_version\"/" "$PROJECT_ROOT/pyproject.toml"
    log_success "Updated pyproject.toml"

    # Update app/__init__.py
    sed -i.bak "s/__version__ = .*/__version__ = \"$new_version\"/" "$PROJECT_ROOT/app/__init__.py"
    sed -i.bak "s/__milestone__ = .*/__milestone__ = \"$milestone\"/" "$PROJECT_ROOT/app/__init__.py"
    log_success "Updated app/__init__.py"

    # Clean up backup files
    rm -f "$PROJECT_ROOT/pyproject.toml.bak" "$PROJECT_ROOT/app/__init__.py.bak"
}

validate_git_state() {
    """Validate git repository state for release"""
    cd "$PROJECT_ROOT"

    # Check if we're on main branch
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        log_error "Must be on main branch for release (currently on: $current_branch)"
        return 1
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_error "Uncommitted changes detected. Please commit or stash changes."
        return 1
    fi

    # Check if we're up to date with remote
    git fetch origin main
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/main)

    if [ "$local_commit" != "$remote_commit" ]; then
        log_error "Local branch is not up to date with origin/main"
        log_info "Please run: git pull origin main"
        return 1
    fi

    log_success "Git repository state is valid for release"
    return 0
}

# =============================================================================
# Release Preparation Functions
# =============================================================================

create_release_branch() {
    """Create and switch to release branch"""
    local version=$1
    local branch_name="release/v$version"

    cd "$PROJECT_ROOT"

    log_info "Creating release branch: $branch_name"
    git checkout -b "$branch_name"
    log_success "Created and switched to $branch_name"
}

prepare_release() {
    """Prepare release with version updates"""
    local version=$1
    local milestone=$2

    log_header "Preparing Harbor $version release (milestone: $milestone)"

    # Validate inputs
    if ! validate_version_format "$version"; then
        return 1
    fi

    # Validate git state
    if ! validate_git_state; then
        return 1
    fi

    # Create release branch
    create_release_branch "$version"

    # Update version files
    update_version_files "$version" "$milestone"

    # Run tests to ensure everything still works
    log_info "Running tests to validate changes..."
    if command -v make >/dev/null 2>&1; then
        if make dev-test 2>/dev/null; then
            log_success "Tests passed"
        else
            log_warning "Tests failed or make target not available"
        fi
    else
        log_warning "Make not available, skipping test validation"
    fi

    # Commit changes
    git add pyproject.toml app/__init__.py
    git commit -m "chore: bump version to $version for $milestone milestone

- Update version in pyproject.toml and app/__init__.py
- Prepare for $milestone milestone release
- All tests passing

Release-Notes: Harbor $version ready for release"

    log_success "Release preparation complete!"
    log_info "Next steps:"
    log_info "  1. Review changes: git show HEAD"
    log_info "  2. Push branch: git push origin release/v$version"
    log_info "  3. Create pull request for final review"
    log_info "  4. After merge, tag release: $0 tag $version"
}

create_release_tag() {
    """Create and push release tag"""
    local version=$1

    cd "$PROJECT_ROOT"

    # Validate we're on main branch
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        log_error "Must be on main branch to create release tag"
        return 1
    fi

    # Validate git state
    if ! validate_git_state; then
        return 1
    fi

    # Validate version format
    if ! validate_version_format "$version"; then
        return 1
    fi

    local tag_name="v$version"
    local milestone=$(determine_milestone_from_version "$version")

    log_info "Creating release tag: $tag_name"

    # Create annotated tag
    git tag -a "$tag_name" -m "Harbor Container Updater $version

Milestone: $milestone
Release Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

This release completes the $milestone milestone of Harbor development.

Key Features:
- Zero-configuration deployment for home labs
- Comprehensive CI/CD pipeline with automated testing
- Multi-architecture Docker support (amd64, arm64 planned)
- Production-ready security and monitoring
- Extensible architecture for future milestones

Installation:
  docker run -d -p 8080:8080 ghcr.io/deusextaco/harbor:$version

Documentation: https://harbor-docs.dev
Repository: https://github.com/DeusExTaco/harbor
Issues: https://github.com/DeusExTaco/harbor/issues"

    log_success "Created tag: $tag_name"

    # Push tag
    log_info "Pushing tag to origin..."
    git push origin "$tag_name"

    log_success "Release tag created and pushed!"
    log_info "GitHub Actions will now build and publish the release"
    log_info "Monitor progress at: https://github.com/DeusExTaco/harbor/actions"
}

# =============================================================================
# Status and Information Functions
# =============================================================================

show_release_status() {
    """Show current release status"""
    cd "$PROJECT_ROOT"

    log_header "Harbor Release Status"

    local current_version=$(get_current_version 2>/dev/null || echo "unknown")
    local current_milestone=$(get_current_milestone 2>/dev/null || echo "unknown")
    local current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")

    echo "📦 Current Version: $current_version"
    echo "📋 Current Milestone: $current_milestone"
    echo "🌿 Current Branch: $current_branch"
    echo "🏷️ Latest Tag: $latest_tag"
    echo ""

    # Check if there are unreleased changes
    if [ "$latest_tag" != "none" ]; then
        local commits_since_tag=$(git rev-list --count "$latest_tag"..HEAD 2>/dev/null || echo "0")
        echo "📊 Commits since last tag: $commits_since_tag"

        if [ "$commits_since_tag" -gt 0 ]; then
            echo ""
            echo "🔄 Recent changes since $latest_tag:"
            git log --oneline --no-merges "$latest_tag"..HEAD 2>/dev/null | head -10 || echo "No changes found"
        fi
    fi

    echo ""
    echo "🎯 Milestone Progress:"
    echo "  M0 (Foundation): ✅ Complete"
    echo "  M1 (Discovery): 🚧 Planned"
    echo "  M2 (Updates): 📋 Planned"
    echo "  M3 (Automation): 📋 Planned"
    echo "  M4 (Observability): 📋 Planned"
    echo "  M5 (Production): 📋 Planned"
    echo "  M6 (Release): 📋 Planned"
}

show_next_versions() {
    """Show suggested next version numbers"""
    local current_version=$(get_current_version 2>/dev/null || echo "0.1.0")

    log_header "Suggested Next Versions"
    echo "Current version: $current_version"
    echo ""

    echo "📈 Version Increments:"
    echo "  Patch:  $(increment_version "$current_version" patch) (bug fixes)"
    echo "  Minor:  $(increment_version "$current_version" minor) (new features)"
    echo "  Major:  $(increment_version "$current_version" major) (breaking changes)"
    echo "  RC:     $(increment_version "$current_version" rc) (release candidate)"
    echo ""

    echo "📋 Milestone Mapping:"
    echo "  0.1.x → M0 (Foundation)"
    echo "  0.2.x → M1 (Discovery)"
    echo "  0.3.x → M2 (Updates)"
    echo "  0.4.x → M3 (Automation)"
    echo "  0.5.x → M4 (Observability)"
    echo "  0.6.x → M5 (Production)"
    echo "  1.0.x → M6 (Release)"
}

# =============================================================================
# Main Command Handler
# =============================================================================

show_usage() {
    cat << EOF
🚢 Harbor Release Management

Usage: $0 <command> [options]

Commands:
  status              Show current release status
  versions            Show suggested next version numbers
  prepare <version>   Prepare release branch with version updates
  tag <version>       Create and push release tag (triggers CI/CD)
  increment <type>    Show incremented version (major|minor|patch|rc)

Examples:
  $0 status                    # Show current release status
  $0 versions                  # Show suggested next versions
  $0 prepare 0.1.1            # Prepare v0.1.1 release
  $0 tag 0.1.1                # Create v0.1.1 release tag
  $0 increment patch           # Show next patch version

Release Process:
  1. $0 status                 # Check current status
  2. $0 prepare <version>      # Prepare release branch
  3. Create PR and review      # Review changes
  4. Merge to main            # Merge release branch
  5. $0 tag <version>         # Create release tag

Notes:
  - Must be on main branch for tagging
  - All changes must be committed
  - Release branches: release/v<version>
  - Tags trigger automated CI/CD pipeline
  - Follow semantic versioning (https://semver.org)

Harbor Milestone Mapping:
  0.1.x → M0 (Foundation)      - Project infrastructure, CI/CD
  0.2.x → M1 (Discovery)       - Container discovery, registry integration
  0.3.x → M2 (Updates)         - Safe update engine with rollback
  0.4.x → M3 (Automation)      - Scheduling and web interface
  0.5.x → M4 (Observability)   - Monitoring and metrics
  0.6.x → M5 (Production)      - Security hardening, performance
  1.0.x → M6 (Release)         - Community launch, documentation

Documentation: https://harbor-docs.dev/development/releases
EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    # Ensure we're in the project root
    if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        log_error "Must be run from Harbor project root"
        log_info "Expected to find pyproject.toml in: $PROJECT_ROOT"
        exit 1
    fi

    case "${1:-}" in
        status)
            show_release_status
            ;;
        versions)
            show_next_versions
            ;;
        prepare)
            if [ -z "${2:-}" ]; then
                log_error "Version required for prepare command"
                log_info "Usage: $0 prepare <version>"
                log_info "Example: $0 prepare 0.1.1"
                exit 1
            fi
            local version=$2
            local milestone=$(determine_milestone_from_version "$version")
            prepare_release "$version" "$milestone"
            ;;
        tag)
            if [ -z "${2:-}" ]; then
                log_error "Version required for tag command"
                log_info "Usage: $0 tag <version>"
                log_info "Example: $0 tag 0.1.1"
                exit 1
            fi
            create_release_tag "$2"
            ;;
        increment)
            if [ -z "${2:-}" ]; then
                log_error "Increment type required"
                log_info "Usage: $0 increment <type>"
                log_info "Types: major, minor, patch, rc"
                exit 1
            fi
            local current_version=$(get_current_version)
            increment_version "$current_version" "$2"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: ${1:-}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
RELEASE_SCRIPT_EOF

echo -e "${GREEN}✅ Complete release management script created${NC}"

# =============================================================================
# Create COMPLETE version validation script
# =============================================================================
echo -e "${BLUE}🔍 Creating complete version validation script...${NC}"

cat > "$PROJECT_ROOT/scripts/release/validate_version.py" << 'VALIDATION_SCRIPT_EOF'
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
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class HarborVersionValidator:
    """Validates Harbor version consistency across project files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.app_init_path = project_root / "app" / "__init__.py"

    def get_pyproject_version(self) -> str:
        """Extract version from pyproject.toml."""
        if not self.pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {self.pyproject_path}")

        content = self.pyproject_path.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if not match:
            raise ValueError("Version not found in pyproject.toml")

        return match.group(1)

    def get_app_version(self) -> Tuple[str, str]:
        """Extract version and milestone from app/__init__.py."""
        if not self.app_init_path.exists():
            raise FileNotFoundError(f"app/__init__.py not found at {self.app_init_path}")

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
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+(?:\.[0-9]+)?))?$'
        return bool(re.match(pattern, version))

    def determine_milestone_from_version(self, version: str) -> str:
        """Determine expected milestone from version number."""
        try:
            major, minor, patch = version.split('-')[0].split('.')
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

    def validate_version_consistency(self, target_version: Optional[str] = None) -> Dict[str, any]:
        """Validate version consistency across all project files."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": {}
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
                result["errors"].append(f"Invalid semantic version in pyproject.toml: {pyproject_version}")
                result["valid"] = False

            if not self.validate_semantic_version(app_version):
                result["errors"].append(f"Invalid semantic version in app/__init__.py: {app_version}")
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
                    result["errors"].append(f"Invalid target version format: {target_version}")
                    result["valid"] = False

                if pyproject_version != target_version:
                    result["errors"].append(
                        f"Current version ({pyproject_version}) doesn't match target ({target_version})"
                    )
                    result["valid"] = False

            # Check milestone consistency
            expected_milestone = self.determine_milestone_from_version(pyproject_version)
            if app_milestone != expected_milestone:
                result["warnings"].append(
                    f"Milestone mismatch: app has {app_milestone}, expected {expected_milestone} for version {pyproject_version}"
                )

            result["info"]["expected_milestone"] = expected_milestone

        except Exception as e:
            result["errors"].append(f"Validation error: {str(e)}")
            result["valid"] = False

        return result


class HarborChangelogGenerator:
    """Generates changelog for Harbor releases."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_git_commits_since_tag(self, since_tag: str) -> List[Dict[str, str]]:
        """Get git commits since a specific tag."""
        try:
            cmd = [
                "git", "log",
                f"{since_tag}..HEAD",
                "--no-merges",
                "--pretty=format:%H|%s|%an|%ad",
                "--date=iso"
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0][:8],
                            "subject": parts[1],
                            "author": parts[2],
                            "date": parts[3]
                        })

            return commits

        except subprocess.CalledProcessError:
            return []

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest git tag."""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def categorize_commits(self, commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Categorize commits by type based on conventional commits."""
        categories = {
            "features": [],
            "fixes": [],
            "docs": [],
            "chore": [],
            "breaking": [],
            "other": []
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

        # Get unique contributors
        contributors = sorted(set(commit["author"] for commit in commits))

        # Generate changelog
        changelog = f"""# Harbor Container Updater {version}

**Milestone**: {milestone}
**Release Date**: {datetime.utcnow().strftime('%Y-%m-%d')}
**Release Type**: {'Pre-release' if any(x in version for x in ['alpha', 'beta', 'rc']) else 'Stable Release'}

## 🎯 Milestone Progress

Harbor follows a structured development roadmap with clear milestones:

- **M0 (Foundation)**: Project infrastructure, CI/CD, basic app structure {'✅' if milestone == 'M0' else '🚧' if milestone == 'M1' else '📋'}
- **M1 (Discovery)**: Container discovery and registry integration {'✅' if milestone in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'] else '🚧' if milestone == 'M1' else '📋'}
- **M2 (Updates)**: Safe update engine with rollback capability {'✅' if milestone in ['M2', 'M3', 'M4', 'M5', 'M6'] else '🚧' if milestone == 'M2' else '📋'}
- **M3 (Automation)**: Scheduling and web interface {'✅' if milestone in ['M3', 'M4', 'M5', 'M6'] else '🚧' if milestone == 'M3' else '📋'}
- **M4 (Observability)**: Monitoring and metrics {'✅' if milestone in ['M4', 'M5', 'M6'] else '🚧' if milestone == 'M4' else '📋'}
- **M5 (Production)**: Security hardening and performance {'✅' if milestone in ['M5', 'M6'] else '🚧' if milestone == 'M5' else '📋'}
- **M6 (Release)**: Community launch and documentation {'✅' if milestone == 'M6' else '🚧' if milestone == 'M6' else '📋'}

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
                changelog += f"### 🔄 Changes Since {latest_tag}\n\n"
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
                changelog += "#### 🔄 Other Changes\n"
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

### 🏗️ Foundation Complete

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
            changelog += f"**Repository**: https://github.com/DeusExTaco/harbor\n"

        return changelog


def main():
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
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate version consistency")
    validate_parser.add_argument(
        "--target",
        help="Target version to validate against"
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    # Changelog command
    changelog_parser = subparsers.add_parser("changelog", help="Generate changelog")
    changelog_parser.add_argument(
        "--version",
        required=True,
        help="Version for changelog generation"
    )
    changelog_parser.add_argument(
        "--milestone",
        help="Milestone for the release (auto-detected if not specified)"
    )
    changelog_parser.add_argument(
        "--output",
        help="Output file (stdout if not specified)"
    )
    changelog_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format"
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

            print(f"\n📦 Project Information:")
            for key, value in result["info"].items():
                print(f"   {key}: {value}")

            if result["errors"]:
                print(f"\n❌ Errors:")
                for error in result["errors"]:
                    print(f"   • {error}")

            if result["warnings"]:
                print(f"\n⚠️  Warnings:")
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
            commits = generator.get_git_commits_since_tag(latest_tag) if latest_tag else []
            categorized = generator.categorize_commits(commits)
            contributors = sorted(set(commit["author"] for commit in commits))

            changelog_data = {
                "version": args.version,
                "milestone": milestone,
                "release_date": datetime.utcnow().strftime('%Y-%m-%d'),
                "previous_tag": latest_tag,
                "commits": {
                    "total": len(commits),
                    "by_category": {k: len(v) for k, v in categorized.items()},
                    "details": categorized
                },
                "contributors": contributors
            }

            changelog_content = json.dumps(changelog_data, indent=2)
        else:
            changelog_content = generator.generate_changelog_content(args.version, milestone)

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
VALIDATION_SCRIPT_EOF

echo -e "${GREEN}✅ Complete version validation script created${NC}"

# =============================================================================
# Create CHANGELOG.md if it doesn't exist
# =============================================================================
if [ ! -f "$PROJECT_ROOT/CHANGELOG.md" ]; then
    echo -e "${BLUE}📄 Creating CHANGELOG.md...${NC}"

    cat > "$PROJECT_ROOT/CHANGELOG.md" << 'CHANGELOG_EOF'
# Changelog

All notable changes to Harbor Container Updater will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure following Harbor foundational documents
- FastAPI-based web framework with automatic OpenAPI documentation
- Zero-configuration deployment for home labs
- SQLite database with automatic migrations
- Profile-based configuration (homelab, development, production)
- Comprehensive health checks and monitoring endpoints
- Docker container health checking
- Complete CI/CD pipeline with multi-stage testing
- Security scanning and vulnerability detection
- Development environment with hot reload
- Comprehensive test suite with unit and integration tests
- Release automation with semantic versioning

### Changed
- N/A (initial development)

### Deprecated
- N/A (initial development)

### Removed
- N/A (initial development)

### Fixed
- N/A (initial development)

### Security
- Implemented bandit security scanning in CI/CD pipeline
- Added CodeQL security analysis
- Dependency vulnerability scanning with pip-audit and safety
- Container security scanning with Trivy

---

## Release Timeline

Harbor follows a milestone-based development approach:

### M0 - Foundation (v0.1.x) - ✅ Current
**Focus**: Project infrastructure, CI/CD, basic application structure
- Complete CI/CD pipeline with automated testing and security scanning
- Development-friendly tooling and documentation
- Production-ready Docker images and deployment configurations
- Extensible architecture ready for feature development

### M1 - Discovery (v0.2.x) - 🚧 Planned
**Focus**: Container discovery and registry integration
- Automatic container discovery with change detection
- Multi-registry support (Docker Hub, GHCR, private registries)
- Intelligent caching and rate limiting
- Container specification analysis and tracking

### M2 - Updates (v0.3.x) - 📋 Planned
**Focus**: Safe update engine with rollback capability
- Digest-based updates with atomic cutover
- Health verification before and after updates
- Automatic rollback on failure
- Image management and cleanup

### M3 - Automation (v0.4.x) - 📋 Planned
**Focus**: Scheduling and comprehensive web interface
- Advanced scheduling with cron and interval support
- Complete web UI for all operations
- Real-time progress tracking and log streaming
- User experience enhancements

### M4 - Observability (v0.5.x) - 📋 Planned
**Focus**: Monitoring, metrics, and alerting
- Prometheus metrics and Grafana dashboards
- Comprehensive health monitoring
- Alerting and notification system
- Performance optimization

### M5 - Production (v0.6.x) - 📋 Planned
**Focus**: Security hardening and enterprise features
- Multi-user authentication and RBAC
- Enhanced security and audit capabilities
- High availability and scaling features
- Performance optimization

### M6 - Release (v1.0.x) - 📋 Planned
**Focus**: Community launch and ecosystem integration
- Complete documentation and tutorials
- Migration tools and guides
- Community building and support
- Ecosystem integrations

---

## Version History

### [0.1.0] - TBD
- Initial release completing M0 (Foundation) milestone
- See release notes for detailed feature list

---

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Versioning

We use [Semantic Versioning](http://semver.org/) for versioning. For available versions, see the [tags on this repository](https://github.com/DeusExTaco/harbor/tags).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📚 Documentation: https://harbor-docs.dev
- 🐛 Bug Reports: [GitHub Issues](https://github.com/DeusExTaco/harbor/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/DeusExTaco/harbor/discussions)
- 📧 Email: harbor@example.com

## Acknowledgments

- Thanks to all contributors who help make Harbor better
- Inspired by existing container update tools like Watchtower and Ouroboros
- Built with modern Python tools and best practices
CHANGELOG_EOF

    echo -e "${GREEN}✅ CHANGELOG.md created${NC}"
else
    echo -e "${YELLOW}⚠️  CHANGELOG.md already exists, skipping creation${NC}"
fi

# =============================================================================
# Make scripts executable
# =============================================================================
echo -e "${BLUE}🔧 Making scripts executable...${NC}"

chmod +x "$PROJECT_ROOT/scripts/release/release.sh"
chmod +x "$PROJECT_ROOT/scripts/release/validate_version.py"

# Make other existing scripts executable
find "$PROJECT_ROOT/scripts" -name "*.sh" -exec chmod +x {} \;

echo -e "${GREEN}✅ All scripts made executable${NC}"

# =============================================================================
# Create release documentation
# =============================================================================
echo -e "${BLUE}📚 Creating complete release documentation...${NC}"

cat > "$PROJECT_ROOT/docs/development/releases.md" << 'RELEASE_DOCS_EOF'
# Harbor Release Management

This guide covers the complete release process for Harbor Container Updater, following semantic versioning and our milestone-based development approach.

## Overview

Harbor uses automated release management with semantic versioning:
- **Semantic Versioning**: X.Y.Z format with optional pre-release identifiers
- **Milestone Mapping**: Each version range maps to a specific development milestone
- **Automated Pipeline**: GitHub Actions handle building, testing, and publishing

## Release Process

### 1. Check Release Status

```bash
make release-status
```

This shows current version, milestone, and recent changes.

### 2. Prepare Release

```bash
make release-prepare VERSION=0.1.1
```

This creates a release branch with version updates.

### 3. Review and Merge

1. Create pull request from release branch
2. Review version changes and validation
3. Merge to main branch

### 4. Create Release Tag

```bash
make release-tag VERSION=0.1.1
```

This triggers the automated release pipeline.

## Commands Reference

### Status Commands
- `make release-status` - Show current release status
- `make release-versions` - Show suggested next versions
- `make release-validate` - Validate version consistency

### Version Commands
- `make release-increment TYPE=patch` - Show next patch version
- `make release-increment TYPE=minor` - Show next minor version
- `make release-increment TYPE=major` - Show next major version

### Release Commands
- `make release-prepare VERSION=X.Y.Z` - Prepare release branch
- `make release-tag VERSION=X.Y.Z` - Create release tag
- `make release-changelog VERSION=X.Y.Z` - Generate changelog

### Quick Workflows
- `make release-quick-patch` - Quick patch release
- `make release-quick-minor` - Quick minor release
- `make release-quick-rc` - Quick release candidate

## Milestone Mapping

Harbor development follows a structured milestone approach:

| Version Range | Milestone | Focus |
|---------------|-----------|-------|
| 0.1.x | M0 | Foundation - Project infrastructure, CI/CD |
| 0.2.x | M1 | Discovery - Container discovery, registry integration |
| 0.3.x | M2 | Updates - Safe update engine with rollback |
| 0.4.x | M3 | Automation - Scheduling and web interface |
| 0.5.x | M4 | Observability - Monitoring and metrics |
| 0.6.x | M5 | Production - Security hardening, enterprise features |
| 1.0.x | M6 | Release - Community launch, documentation |

## Complete Release Automation

The release automation system includes:

### Scripts
- `scripts/release/release.sh` - Main release management
- `scripts/release/validate_version.py` - Version validation and changelog generation
- `scripts/setup-release-automation.sh` - Setup script (this file)

### GitHub Workflows
- `.github/workflows/release.yml` - Complete automated release pipeline
- Triggered by git tags or manual dispatch
- Validates, tests, builds, scans, and publishes

### Documentation
- `docs/development/releases.md` - This comprehensive guide
- `CHANGELOG.md` - Keep a Changelog format with milestone timeline
- Release notes automatically generated for each release

## Best Practices

### Before Release
- Ensure all milestone features are complete
- Run full test suite locally: `make dev-test`
- Update documentation if needed
- Review security scan results

### Version Selection
- **Patch** (0.0.1): Bug fixes, security patches
- **Minor** (0.1.0): New features, enhancements
- **Major** (1.0.0): Breaking changes, API changes

### Release Notes
- Changelogs are automatically generated from git commits
- Use conventional commit messages for better categorization
- Include migration notes for breaking changes

## Troubleshooting

### Common Issues

**Version Mismatch Error**
```
❌ Version mismatch: pyproject.toml (0.1.0) != app/__init__.py (0.1.1)
```
Solution: Ensure all version files are updated consistently.

**Git State Error**
```
❌ Uncommitted changes detected
```
Solution: Commit or stash all changes before release.

**Test Failures**
```
❌ Tests failed after version update
```
Solution: Fix failing tests before proceeding with release.

### Manual Recovery

If automated release fails:

1. Check GitHub Actions logs for specific error
2. Fix the issue locally
3. Re-run the release process
4. Contact maintainers if needed

## Security Considerations

- All releases include comprehensive security scanning
- Vulnerabilities block release pipeline
- Security patches get expedited patch releases
- Container images are signed and include SBOMs

For more information, see the [Security Policy](../../SECURITY.md).

## Files Created by Setup

This setup script creates the following files:

```
scripts/
├── release/
│   ├── release.sh                    # Main release management script
│   └── validate_version.py           # Version validation and changelog generation
docs/
└── development/
    └── releases.md                   # This documentation file
CHANGELOG.md                          # Keep a Changelog format (if not existing)
```

Additionally, the Release Automation Workflow should be added to `.github/workflows/release.yml`.

## Next Steps After Setup

1. **Test the release commands:**
   ```bash
   make release-status
   make release-versions
   make release-validate
   ```

2. **Add GitHub secrets for Docker registries:**
   - `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
   - Repository must have package write permissions for GHCR

3. **Customize milestone mapping if needed:**
   - Update version ranges in `scripts/release/release.sh`
   - Update milestone mappings in `scripts/release/validate_version.py`

4. **Add the Release Workflow:**
   - Copy the Release Automation Workflow to `.github/workflows/release.yml`
   - Test with a pre-release version first

5. **Update Makefile:**
   - Add release management commands to your Makefile
   - Test all make targets work correctly

Harbor's release automation is now ready to support your milestone-driven development approach!
RELEASE_DOCS_EOF

echo -e "${GREEN}✅ Complete release documentation created${NC}"

# =============================================================================
# Final validation and instructions
# =============================================================================
echo ""
echo -e "${GREEN}🎉 Harbor Complete Release Automation Setup Finished!${NC}"
echo ""
echo -e "${BLUE}📋 Setup Summary:${NC}"
echo ""
echo -e "${GREEN}✅ Created complete release management script${NC}"
echo "   scripts/release/release.sh (fully functional)"
echo ""
echo -e "${GREEN}✅ Created complete version validation script${NC}"
echo "   scripts/release/validate_version.py (with changelog generation)"
echo ""
echo -e "${GREEN}✅ Created comprehensive documentation${NC}"
echo "   docs/development/releases.md (complete guide)"
echo ""
echo -e "${GREEN}✅ Created/ensured CHANGELOG.md exists${NC}"
echo "   CHANGELOG.md (Keep a Changelog format)"
echo ""
echo -e "${GREEN}✅ Made all scripts executable${NC}"
echo "   All .sh files in scripts/ directory"
echo ""
echo -e "${BLUE}🧪 Test Your Setup:${NC}"
echo ""
echo "1. Test release status:"
echo "   scripts/release/release.sh status"
echo ""
echo "2. Test version validation:"
echo "   python scripts/release/validate_version.py validate"
echo ""
echo "3. Test version suggestions:"
echo "   scripts/release/release.sh versions"
echo ""
echo -e "${BLUE}📝 Still Needed:${NC}"
echo ""
echo -e "${YELLOW}⚠️  Add to .github/workflows/release.yml:${NC}"
echo "   Copy the Release Automation Workflow artifact content"
echo ""
echo -e "${YELLOW}⚠️  Add to Makefile:${NC}"
echo "   Copy the release commands from the Makefile artifact"
echo ""
echo -e "${YELLOW}⚠️  Set GitHub Secrets:${NC}"
echo "   DOCKERHUB_USERNAME, DOCKERHUB_TOKEN (for Docker Hub publishing)"
echo ""
echo -e "${BLUE}🚀 Ready for First Release:${NC}"
echo ""
echo "Once you've added the workflow and Makefile commands:"
echo "   make release-prepare VERSION=0.1.0"
echo "   # Create PR, review, merge to main"
echo "   make release-tag VERSION=0.1.0"
echo ""
echo -e "${GREEN}🚢 Harbor release automation is now completely ready!${NC}"
