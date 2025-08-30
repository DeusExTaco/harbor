# Changelog

All notable changes to Harbor Container Updater will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

### Security
-

## [0.1.0-alpha.4] - 2025-08-30

### Added
- Implement enhanced security and size optimizations
- Add unified PR comment system for CI/CD pipeline summaries

### Changed
- Centralize version extraction with composite action
- Optimize pipeline with caching and early exits

### Fixed
- Resolve Docker build and version bump workflow issues
- Fix Docker entrypoint to support both runtime and test execution
- Complete migration to composite action for version extraction
- Fixed duplication issue in version-bump.yml
- Remove parentheses from echo statement in docker-build
- Correct Python quote escaping in version extraction
- Correct PR comment generation in test and security workflows
- Prevent PR comment job from running without valid PR context
- Correct version extraction regex in version-bump workflow
- Remove inline comments from YAML conditions
- Prevent PR comment actions from running on non-PR events
- Prevent duplicate PR comments
- Update workflows for proper version syncing and auto-tagging

## [0.1.0-alpha.3] - 2024-XX-XX

### Added
- Automated version bumping workflow for develop branch
- Version synchronization between `app/__init__.py` and `pyproject.toml`
- Simplified GitHub release process with auto-generated notes

### Changed
- Docker build workflow now only triggers via main CI/CD pipeline
- Version detection now uses `app/__init__.py` as source of truth
- Release notes generation simplified for M0 milestone

### Fixed
- Eliminated duplicate Docker builds from multiple triggers
- Version consistency between configuration files

## [0.1.0-alpha.2] - 2024-01-XX

### Added
- Comprehensive CI/CD pipeline with multi-stage testing
- Docker multi-registry support (Docker Hub and GHCR)
- Security scanning with CodeQL, Trivy, and dependency checks
- Python 3.11, 3.12, and 3.13 compatibility testing
- Automated release creation for tagged versions

### Changed
- Restructured project to follow Harbor architecture specifications
- Updated configuration system with deployment profiles
- Enhanced error handling and logging

### Fixed
- Configuration loading issues in different environments
- Docker build caching for faster CI/CD runs

## [0.1.0-alpha.1] - 2024-01-XX

### Added
- Initial M0 Foundation implementation
- FastAPI-based web framework with automatic OpenAPI documentation
- SQLite database with SQLAlchemy ORM and Alembic migrations
- Profile-based configuration (homelab, development, production)
- Basic authentication system with session management
- Comprehensive health check and monitoring endpoints
- Docker and Docker Compose deployment configurations
- GitHub Actions CI/CD pipeline foundation
- Project structure following Harbor specifications

### Changed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

### Security
- Implemented secure password hashing with Argon2id
- Added CSRF protection for web interface
- Configured security headers and rate limiting

## Version History

- `0.1.0-alpha.X` - M0 Foundation Phase (Current)
- `0.2.0-alpha.X` - M1 Container Discovery (Planned)
- `0.3.0-alpha.X` - M2 Update Engine (Planned)
- `0.4.0-alpha.X` - M3 Automation (Planned)
- `0.5.0-beta.X` - M4 Observability (Planned)
- `0.6.0-beta.X` - M5 Production Ready (Planned)
- `1.0.0` - M6 Release (Planned)

[Unreleased]: https://github.com/DeusExTaco/harbor/compare/v0.1.0-alpha.3...HEAD
[0.1.0-alpha.3]: https://github.com/DeusExTaco/harbor/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/DeusExTaco/harbor/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/DeusExTaco/harbor/releases/tag/v0.1.0-alpha.1
