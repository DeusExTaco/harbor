# Contributing to Harbor Container Updater

🎉 **Thank you for your interest in contributing to Harbor!**

Harbor is designed to be **home lab friendly first**, with enterprise features
added progressively. We welcome contributions from developers of all skill
levels, whether you're fixing a typo, adding a feature, or improving
documentation.

## 📋 Table of Contents

- Quick Start for Contributors
- How to Contribute
- Development Environment Setup
- Code Standards and Style
- Testing Guidelines
- Submitting Changes
- Project Structure
- Development Workflow
- Community Guidelines
- Getting Help

## 🚀 Quick Start for Contributors

### Prerequisites

- **Python 3.11+** (Python 3.13 recommended)
- **Docker** (for container testing)
- **Git** (for version control)
- **PyCharm** (recommended IDE) or your preferred editor

### 5-Minute Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/harbor.git
cd harbor

# 2. Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install development dependencies
pip install -e ".[dev]"

# 4. Set up pre-commit hooks
pre-commit install

# 5. Run tests to verify setup
make test

# 6. Start developing!
make help  # See all available commands
```

## 🤝 How to Contribute

### Types of Contributions We Welcome

#### 🐛 **Bug Reports**

- Use the bug report template (.github/ISSUE_TEMPLATE/bug_report.yml)
- Include clear reproduction steps
- Provide environment details (OS, Docker version, etc.)

#### ✨ **Feature Requests**

- Use the feature request template (.github/ISSUE_TEMPLATE/feature_request.yml)
- Consider Harbor's "home lab first" philosophy
- Explain the use case and problem being solved

#### 📝 **Documentation**

- Fix typos and improve clarity
- Add examples and use cases
- Update API documentation
- Create tutorials and guides

#### 💻 **Code Contributions**

- Bug fixes
- New features (discuss in an issue first)
- Performance improvements
- Test coverage improvements

#### 🎨 **UI/UX Improvements**

- Web interface enhancements
- Mobile responsiveness
- Accessibility improvements
- User experience optimizations

### Good First Issues

Look for issues labeled with:

- `good first issue` - Perfect for newcomers
- `help wanted` - We'd love community help
- `documentation` - Documentation improvements
- `homelab` - Home lab focused improvements

## 🛠️ Development Environment Setup

### Detailed Setup Instructions

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/harbor.git
cd harbor

# Add upstream remote
git remote add upstream https://github.com/DeusExTaco/harbor.git
```

#### 2. Python Environment

```bash
# Create virtual environment with Python 3.13
python3.13 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

#### 3. Development Tools Setup

```bash
# Install pre-commit hooks
pre-commit install

# Verify installation
pre-commit run --all-files

# Set up git hooks
make git-setup
```

#### 4. IDE Configuration (PyCharm)

1. **Open Project**: File → Open → Select harbor directory
2. **Set Interpreter**: Settings → Project → Python Interpreter → Select
   `.venv/bin/python`
3. **Mark Directories**:
   - Right-click `app/` → Mark Directory as → Sources Root
   - Right-click `tests/` → Mark Directory as → Test Sources Root
4. **Configure Run Configuration**:
   - Run → Edit Configurations → Add Python configuration
   - Script: `app/main.py`
   - Environment: `HARBOR_MODE=development`

#### 5. Verify Setup

```bash
# Run all tests
make test

# Run linting
make lint

# Check code formatting
make format

# Run the application
make run
```

### Development Dependencies

- **Testing**: pytest, pytest-cov, pytest-asyncio, pytest-mock
- **Code Quality**: ruff, mypy, black, pre-commit
- **Development**: ipython, rich (for pretty printing)
- **E2E Testing**: playwright (for browser testing)

## 🎨 Code Standards and Style

### Python Code Style

Harbor follows **PEP 8** with some modifications:

```python
# ✅ Good: Clear, descriptive names
class ContainerDiscoveryService:
    """Service for discovering and managing Docker containers."""

    async def discover_containers(
        self, include_stopped: bool = True
    ) -> List[ContainerInfo]:
        """Discover containers with optional filtering."""
        # Implementation here
        pass

# ✅ Good: Type hints and docstrings
def update_container(container_id: str, target_digest: str) -> UpdateResult:
    """
    Update a container to a specific image digest.

    Args:
        container_id: Unique container identifier
        target_digest: SHA256 digest of target image

    Returns:
        UpdateResult with success status and details

    Raises:
        ContainerNotFoundError: If container doesn't exist
        UpdateFailedError: If update process fails
    """
    # Implementation here
    pass
```

### Code Organization

```python
# File structure for new modules
"""
Module docstring explaining purpose and usage.

This module implements [specific functionality] for Harbor.
It follows the [pattern/architecture] and integrates with [other components].
"""

# Standard library imports
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import httpx
from pydantic import BaseModel, Field

# Local application imports
from app.config import get_settings
from app.db.models.container import Container
from app.services.base import BaseService


# Module-level constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
```

### Formatting Rules

- **Line Length**: 88 characters (Black default)
- **Imports**: Use isort for import organization
- **Quotes**: Double quotes preferred
- **Trailing Commas**: Required for multi-line structures

### Automated Formatting

```bash
# Format code automatically
make format

# Check formatting without changing files
ruff format --check app/ tests/
black --check app/ tests/
```

### Type Hints

Harbor uses **comprehensive type hints**:

```python
# ✅ Required: Function signatures
def process_container(container: Container) -> ProcessResult:
    pass

# ✅ Required: Class attributes
class ContainerPolicy:
    auto_update_enabled: bool = True
    update_schedule: Optional[str] = None

# ✅ Required: Complex types
UpdateCallback = Callable[[Container, UpdateResult], Awaitable[None]]
ConfigDict = Dict[str, Union[str, int, bool]]
```

## 🧪 Testing Guidelines

### Test Organization

```text
tests/
├── unit/                 # Fast, isolated tests
│   ├── auth/            # Authentication tests
│   ├── services/        # Business logic tests
│   └── utils/           # Utility function tests
├── integration/         # Component interaction tests
├── e2e/                # End-to-end workflow tests
├── performance/        # Performance and load tests
└── security/           # Security-focused tests
```

### Writing Tests

#### Unit Tests

```python
# tests/unit/services/test_discovery.py
import pytest
from unittest.mock import Mock, patch

from app.services.discovery import DiscoveryService
from app.models.container import Container


class TestDiscoveryService:
    """Test container discovery functionality."""

    @pytest.fixture
    def discovery_service(self):
        """Create discovery service instance for testing."""
        return DiscoveryService()

    @pytest.mark.unit
    async def test_discover_containers_success(self, discovery_service):
        """Test successful container discovery."""
        # Arrange
        mock_containers = [
            Container(name="test-container", image="nginx:latest"),
        ]

        with patch('app.runtimes.docker.DockerRuntime.list_containers') as mock_list:
            mock_list.return_value = mock_containers

            # Act
            result = await discovery_service.discover_containers()

            # Assert
            assert len(result) == 1
            assert result[0].name == "test-container"
            mock_list.assert_called_once()

    @pytest.mark.unit
    async def test_discover_containers_error_handling(self, discovery_service):
        """Test error handling during discovery."""
        with patch('app.runtimes.docker.DockerRuntime.list_containers') as mock_list:
            mock_list.side_effect = Exception("Docker unavailable")

            # Should handle gracefully
            result = await discovery_service.discover_containers()
            assert result == []
```

#### Integration Tests

```python
# tests/integration/test_update_workflow.py
import pytest
import tempfile
from pathlib import Path

from app.services.updater import UpdateService
from app.db.session import get_session


class TestUpdateWorkflow:
    """Test complete update workflows."""

    @pytest.mark.integration
    async def test_complete_update_workflow(self, test_database):
        """Test complete container update process."""
        # This test uses a real database and Docker container
        # but in a controlled test environment
        pass
```

### Test Commands

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-cov

# Run specific test file
pytest tests/unit/services/test_discovery.py -v

# Run tests matching pattern
pytest -k "test_discovery" -v
```

### Test Requirements

- **Coverage**: Aim for >90% test coverage
- **Speed**: Unit tests should run in <1 second each
- **Isolation**: Use mocks for external dependencies
- **Clear Names**: Test names should describe what they test
- **Documentation**: Complex tests need docstrings

## 📤 Submitting Changes

### Branch Naming

```bash
# Feature branches
git checkout -b feature/container-health-checks
git checkout -b feature/api-authentication

# Bug fix branches  
git checkout -b fix/discovery-memory-leak
git checkout -b fix/schedule-timezone-handling

# Documentation branches
git checkout -b docs/api-reference-update
git checkout -b docs/deployment-guide
```

### Commit Message Format

```bash
# Format: <type>(<scope>): <description>
#
# Types: feat, fix, docs, style, refactor, test, chore
# Scope: component being changed (optional)
# Description: concise description of change

# Examples:
git commit -m "feat(discovery): add support for Docker Compose labels"
git commit -m "fix(updater): handle registry timeout errors gracefully"
git commit -m "docs(api): add examples for container policy endpoints"
git commit -m "test(integration): add tests for update rollback workflow"
```

### Pull Request Process

#### 1. Before Submitting

```bash
# Update your branch with latest changes
git fetch upstream
git rebase upstream/develop

# Run full test suite
make test

# Run code quality checks
make lint
make format

# Verify pre-commit hooks pass
pre-commit run --all-files
```

#### 2. Pull Request Description

Use our PR template (.github/PULL_REQUEST_TEMPLATE.md) and include:

- **Clear description** of changes
- **Issue reference** (e.g., "Closes #123")
- **Testing performed** (unit, integration, manual)
- **Breaking changes** (if any)
- **Screenshots** (for UI changes)

#### 3. Review Process

- **Automated checks** must pass (CI/CD pipeline)
- **Code review** by maintainers
- **Home lab compatibility** verification
- **Documentation** updates if needed

#### 4. Merge Requirements

- ✅ All CI/CD checks passing
- ✅ Code review approval
- ✅ No merge conflicts
- ✅ Documentation updated
- ✅ Tests added/updated

## 🗃️ Project Structure

### Application Architecture

```text
harbor/
├── app/                    # Main application code
│   ├── api/               # FastAPI route handlers
│   ├── auth/              # Authentication & authorization
│   ├── db/                # Database models & migrations
│   ├── services/          # Business logic layer
│   ├── runtimes/          # Container runtime abstraction
│   ├── web/               # Web UI (templates, static files)
│   └── config.py          # Configuration management
│
├── tests/                 # Test suite
├── deploy/                # Deployment configurations
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── examples/              # Example configurations
```

### Key Design Principles

1. **Home Lab First**: Simple defaults, progressive complexity
2. **Runtime Abstraction**: Support multiple container runtimes
3. **Service Layer**: Clean separation of business logic
4. **Type Safety**: Comprehensive type hints throughout
5. **Async by Default**: Modern async/await patterns

## 🔄 Development Workflow

### Daily Development

```bash
# Start your day
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test frequently
make test-unit  # Fast feedback loop

# Commit early and often
git add .
git commit -m "feat: implement basic feature structure"

# Before pushing
make test      # Full test suite
make lint      # Code quality
pre-commit run --all-files  # Final checks

# Push and create PR
git push origin feature/your-feature-name
```

### Feature Development

1. **Plan**: Create or comment on an issue
2. **Branch**: Create feature branch from `develop`
3. **Develop**: Write code, tests, documentation
4. **Test**: Ensure all tests pass
5. **Review**: Self-review changes
6. **Submit**: Create pull request
7. **Iterate**: Address review feedback
8. **Merge**: Maintainer merges when ready

### Release Process

- **develop**: Active development branch
- **main**: Stable release branch
- **Releases**: Tagged semantic versions (v0.1.0, v0.2.0, etc.)

## 🏠 Home Lab Philosophy

Harbor is designed for **home lab users first**. When contributing, consider:

### ✅ Home Lab Friendly

- **Zero Configuration**: Works out of the box
- **Resource Efficient**: Runs on Raspberry Pi
- **Simple Defaults**: Sensible settings for home use
- **Progressive Disclosure**: Advanced features don't overwhelm beginners

### ❌ Avoid Enterprise Complexity

- **Don't require** external databases for basic features
- **Don't assume** enterprise network setups
- **Don't add** unnecessary complexity
- **Don't break** simple use cases

### Example: Feature Decision Matrix

| Feature | Home Lab Impact | Enterprise Value | Decision |
|---------|----------------|------------------|----------|
| SQLite support | ✅ Essential | ➖ Limited | ✅ Implement |
| MFA/TOTP | ➖ Optional | ✅ Required | 🚩 Feature flag |
| Auto-discovery | ✅ Essential | ✅ Essential | ✅ Implement |
| LDAP integration | ❌ Complex | ✅ Required | 🚩 Feature flag |

## 👥 Community Guidelines

### Code of Conduct

We follow the [Contributor Covenant](CODE_OF_CONDUCT.md). In summary:

- **Be respectful** and inclusive
- **Welcome newcomers** and help them succeed
- **Focus on constructive feedback**
- **Assume good intentions**

### Communication

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, showcase
- **Pull Requests**: Code reviews and technical discussion

### Recognition

Contributors are recognized in:

- Release notes for significant contributions
- README contributors section
- GitHub contributor statistics

## 🆘 Getting Help

### For Contributors

- **Development Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Documentation**: Check `docs/` directory

### For Users

- **Installation Help**: See Getting Started Guide
  (docs/getting-started/home-lab.md)
- **Configuration Questions**: See Configuration Docs (docs/configuration/)
- **Troubleshooting**: See Troubleshooting Guide (docs/troubleshooting/)

## 📚 Additional Resources

### Documentation

- [Architecture Overview](docs/development/architecture.md)
- [API Reference](docs/api/)
- [Deployment Guides](docs/deployment/)

### Development Tools

- [PyCharm Setup Guide](docs/development/pycharm-setup.md)
- [Testing Guide](docs/development/testing.md)
- [Debugging Guide](docs/development/debugging.md)

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker API Documentation](https://docker-py.readthedocs.io/)

---

## 🎉 Thank You

Your contributions help make Harbor better for home lab users everywhere.
Whether you're fixing a typo, adding a feature, or improving documentation,
every contribution matters.

**Happy coding!** 🚀

---

*This document is a living guide. If you find ways to improve it, please
submit a pull request!*
