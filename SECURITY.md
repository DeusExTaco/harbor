# Security Policy

## Supported Versions

Harbor Container Updater follows semantic versioning.
Security updates are provided for:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please send security reports to:
[security@harbor-project.org](mailto:security@harbor-project.org)

You should receive a response within 48 hours. If the issue is confirmed, we will:

1. Acknowledge the vulnerability
2. Assign a CVE if necessary  
3. Develop and test a fix
4. Release a security update
5. Publicly disclose the vulnerability after the fix is available

## Security Considerations for Harbor

### Container Security

- Harbor runs as non-root user in containers
- Docker socket access is required but can be proxied for security
- Sensitive data is encrypted at rest

### Network Security

- HTTPS can be enforced in production deployments
- Rate limiting protects against abuse
- No telemetry or "phone home" functionality

### Dependency Security

- Dependencies are regularly updated
- Vulnerability scanning in CI/CD pipeline
- Minimal dependency footprint to reduce attack surface

### Data Protection

- No user data leaves the system unless explicitly configured
- Database encryption available for sensitive deployments
- Audit logging for compliance requirements

## Vulnerability Management

### Development Phase (v0.x)

During the pre-1.0 development phase:

- **Critical/High vulnerabilities**: Fixed immediately
- **Moderate vulnerabilities**: Fixed in next release cycle
- **Low vulnerabilities**: Fixed during regular maintenance

### Production Phase (v1.0+)

After v1.0 release:

- **Critical vulnerabilities**: Emergency patch within 24 hours
- **High vulnerabilities**: Patch within 7 days
- **Moderate vulnerabilities**: Patch within 30 days
- **Low vulnerabilities**: Addressed in regular releases

## Security Features

### Current (M0-M6)

- Secure password hashing (Argon2)
- Session management with secure cookies
- CSRF protection
- Input validation and sanitization
- Docker socket proxy support

### Planned (M7+)

- Multi-factor authentication (TOTP)
- Role-based access control (RBAC)
- Audit logging with integrity protection
- External authentication (LDAP/SAML)
- Database encryption at rest

## License Compliance

Harbor uses only permissive open-source licenses:

- **Allowed**: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, PSF-2.0
- **Not allowed**: GPL-2.0, AGPL-3.0, proprietary licenses

## Security Testing

- Static analysis with bandit
- Dependency vulnerability scanning
- Container image scanning
- Pre-commit security hooks

## Contact

For security concerns: <security@harbor-project.org>
For general questions: <https://github.com/harbor/harbor/discussions>
