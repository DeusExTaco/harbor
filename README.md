# Harbor Container Updater

Automated Docker container updates for home labs and enterprises.

## Status

🚧 **Development Phase: M0 (Foundation)** 🚧

Harbor is currently in early development. The foundation and core infrastructure
are being built according to our 14-week milestone plan.

## Quick Start (Coming Soon)

```bash
docker run -d --restart unless-stopped -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  ghcr.io/deusextaco/harbor:latest
```

## Development Status

- [x] M0: Foundation (Weeks 1-2) - **IN PROGRESS**
- [ ] M1: Discovery (Weeks 3-4)
- [ ] M2: Update Engine (Weeks 5-6)
- [ ] M3: Automation (Weeks 7-8)
- [ ] M4: Observability (Weeks 9-10)
- [ ] M5: Production Ready (Weeks 11-12)
- [ ] M6: Release (Weeks 13-14)

## Features (Planned)

### 🏠 Home Lab Optimized

- Zero-configuration deployment
- Auto-discovery of containers
- Resource efficient (Raspberry Pi support)
- Simple web interface

### 🏢 Enterprise Ready

- Multi-user RBAC
- Comprehensive audit trails
- High availability deployment
- Advanced monitoring

## Contributing

Harbor is an open source project. See CONTRIBUTING.md for development setup.

## License

MIT License - see LICENSE file for details.

echo "" >> README.md
echo "<!-- M0 Foundation Complete -->" >> README.md
