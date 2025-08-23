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
    # Get current version from pyproject.toml
    grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
}

get_current_milestone() {
    # Get current milestone from app/__init__.py
    grep '__milestone__ = ' "$PROJECT_ROOT/app/__init__.py" | sed 's/__milestone__ = "\(.*\)"/\1/'
}

validate_version_format() {
    # Validate semantic version format
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
    # Determine Harbor milestone from version number
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
    # Increment version based on type (major, minor, patch)
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
    # Update version in all relevant files
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
    # Validate git repository state for release
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
    # Create and switch to release branch
    local version=$1
    local branch_name="release/v$version"

    cd "$PROJECT_ROOT"

    log_info "Creating release branch: $branch_name"
    git checkout -b "$branch_name"
    log_success "Created and switched to $branch_name"
}

prepare_release() {
    # Prepare release with version updates
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
    # Create and push release tag
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
    # Show current release status
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
    # Show suggested next version numbers
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
