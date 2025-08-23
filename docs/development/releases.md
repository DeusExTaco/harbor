# Harbor Release Management

This guide covers the complete release process for Harbor Container Updater,
following semantic versioning and our milestone-based development approach.

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

#### Version Mismatch Error

```text
❌ Version mismatch: pyproject.toml (0.1.0) != app/__init__.py (0.1.1)
```

Solution: Ensure all version files are updated consistently.

#### Git State Error

```text
❌ Uncommitted changes detected
```

Solution: Commit or stash all changes before release.

#### Test Failures

```text
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

```text
scripts/
├── release/
│   ├── release.sh                    # Main release management script
│   └── validate_version.py           # Version validation and changelog generation
docs/
└── development/
    └── releases.md                   # This documentation file
CHANGELOG.md                          # Keep a Changelog format (if not existing)
```

Additionally, the Release Automation Workflow should be added to
`.github/workflows/release.yml`.

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

Harbor's release automation is now ready to support your milestone-driven
development approach!
