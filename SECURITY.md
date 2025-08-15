# Security Policy

## Supported Versions

Harbor follows semantic versioning. Security updates are provided for the
following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

The Harbor team takes security vulnerabilities seriously. We appreciate your
efforts to responsibly disclose your findings.

### Private Vulnerability Reporting

For security vulnerabilities, please use GitHub's private vulnerability
reporting feature:

1. Go to the [Harbor repository security tab][sec-tab]
2. Click "Report a vulnerability"
3. Fill out the vulnerability report form

This ensures that vulnerability details are not publicly disclosed until a fix
is available.

### What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Impact**: What could an attacker achieve by exploiting this vulnerability?
- **Reproduction**: Step-by-step instructions to reproduce the issue
- **Environment**: Harbor version, operating system, Docker version, etc.
- **Proof of Concept**: Code or screenshots demonstrating the vulnerability
  (if applicable)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Vulnerability Assessment**: Within 1 week
- **Fix Timeline**: Critical vulnerabilities will be addressed within 2 weeks

### Disclosure Policy

- Harbor follows coordinated disclosure
- We will work with you to understand and fix the vulnerability
- Once fixed, we will publicly acknowledge your contribution (unless you prefer
  to remain anonymous)
- Security advisories will be published for significant vulnerabilities

## Security Measures

Harbor implements multiple security layers:

### Application Security

- **Input Validation**: All user inputs are validated and sanitized
- **Authentication**: Secure session management and API key authentication
- **Authorization**: Role-based access control (future versions)
- **Secrets Management**: Encrypted storage of sensitive data

### Container Security

- **Non-root Execution**: Harbor containers run as non-root user
- **Minimal Attack Surface**: Distroless/minimal base images
- **Security Scanning**: Automated vulnerability scanning with Trivy
- **Dependency Management**: Regular security updates for dependencies

### Infrastructure Security

- **Docker Socket**: Support for Docker socket proxy to limit API access
- **Network Security**: Configurable network policies
- **Resource Limits**: CPU and memory limits to prevent resource exhaustion

### Development Security

- **Secure Development**: Security-focused code review process
- **Automated Scanning**: Multiple security scanning tools in CI/CD
- **Dependency Scanning**: Automated vulnerability detection in dependencies
- **Secret Scanning**: Automated detection of accidentally committed secrets

## Security Configuration

### Home Lab Security (Default)

```yaml
security_level: homelab
features:
  - HTTP allowed on internal networks
  - Session-based authentication
  - Basic CSRF protection
  - Docker socket access (with proxy option)
```

### Production Security

```yaml
security_level: production
features:
  - HTTPS required
  - Strong password requirements
  - Docker socket proxy mandatory
  - API key authentication required
  - Enhanced audit logging
```

## Security Best Practices

### For Users

1. **Keep Harbor Updated**: Install security updates promptly
2. **Use HTTPS**: Enable HTTPS in production environments
3. **Docker Socket Proxy**: Use a Docker socket proxy instead of direct socket
   access
4. **Strong Passwords**: Use strong, unique passwords
5. **Network Security**: Run Harbor on isolated networks when possible
6. **Regular Backups**: Maintain secure backups of Harbor data

### For Developers

1. **Security Reviews**: All code changes undergo security review
2. **Dependency Updates**: Keep dependencies updated with security patches
3. **Input Validation**: Validate all inputs at API boundaries
4. **Secret Management**: Never commit secrets to version control
5. **Least Privilege**: Follow principle of least privilege

## Security Contact

For urgent security matters, you can also reach out to:

- GitHub Security: Use private vulnerability reporting
- Project Maintainers: Through GitHub discussions (for non-sensitive security
  questions)

## Acknowledgments

We thank the security community for helping keep Harbor and our users safe.
Security researchers who responsibly disclose vulnerabilities will be
acknowledged in our security advisories (with their permission).

---

**Note**: This security policy applies to the Harbor container updater project.
For security issues with Docker, container registries, or other external
dependencies, please report them to the respective projects.

[sec-tab]: https://github.com/DeusExTaco/harbor/security
