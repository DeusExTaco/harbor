#!/usr/bin/env python3
"""
Harbor Container Updater - Multi-Architecture Validation Script

Validates that the development environment is properly configured for
multi-architecture builds and testing.

Following Harbor Project Structure from foundational documents.
"""

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any


class MultiArchValidator:
    """Validates multi-architecture development environment."""

    def __init__(self):
        self.host_arch = platform.machine().lower()
        self.host_os = platform.system()
        self.project_root = Path(__file__).parent.parent.parent
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def validate_docker_setup(self) -> bool:
        """Validate Docker and buildx setup."""
        print("🐳 Validating Docker Environment...")

        # Check Docker availability
        try:
            result = subprocess.run(['docker', '--version'],
                                    capture_output=True, text=True, check=True)
            docker_version = result.stdout.strip()
            print(f"   ✅ Docker: {docker_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.issues.append("Docker is not installed or not accessible")
            return False

        # Check Docker buildx
        try:
            result = subprocess.run(['docker', 'buildx', 'version'],
                                    capture_output=True, text=True, check=True)
            buildx_version = result.stdout.strip()
            print(f"   ✅ Buildx: {buildx_version}")
        except subprocess.CalledProcessError:
            self.issues.append("Docker buildx is not available")
            return False

        # Check buildx builders
        try:
            result = subprocess.run(['docker', 'buildx', 'ls'],
                                    capture_output=True, text=True, check=True)
            builders = result.stdout
            if 'linux/amd64' in builders and 'linux/arm64' in builders:
                print("   ✅ Multi-platform builders available")
            else:
                self.warnings.append("Multi-platform builders may need setup")
        except subprocess.CalledProcessError:
            self.warnings.append("Could not check buildx builders")

        return True

    def validate_qemu_setup(self) -> bool:
        """Validate QEMU emulation for cross-platform builds."""
        print("🔄 Validating QEMU Emulation...")

        try:
            # Check if QEMU emulation is registered
            result = subprocess.run(['docker', 'run', '--rm', '--privileged',
                                     'multiarch/qemu-user-static', '--reset', '-p', 'yes'],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("   ✅ QEMU emulation configured")
                return True
            else:
                self.warnings.append("QEMU emulation may not be properly configured")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.warnings.append("Could not configure QEMU emulation")

        # Check what platforms are available
        try:
            result = subprocess.run(['docker', 'buildx', 'inspect', '--bootstrap'],
                                    capture_output=True, text=True, check=True)
            if 'linux/arm64' in result.stdout and 'linux/arm' in result.stdout:
                print("   ✅ ARM emulation appears available")
                return True
        except subprocess.CalledProcessError:
            pass

        return False

    def validate_project_structure(self) -> bool:
        """Validate Harbor project structure."""
        print("📁 Validating Project Structure...")

        required_files = [
            'deploy/docker/Dockerfile',
            'deploy/docker/docker-compose.dev.yml',
            'pyproject.toml',
            'app/__init__.py',
            'app/main.py',
            'Makefile',
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
            else:
                print(f"   ✅ {file_path}")

        if missing_files:
            self.issues.extend([f"Missing required file: {f}" for f in missing_files])
            return False

        return True

    def validate_platform_configs(self) -> bool:
        """Validate platform-specific configurations exist."""
        print("⚙️ Validating Platform Configurations...")

        config_files = [
            'config/homelab.yaml',
            'examples/home-lab/raspberry-pi/docker-compose.yml',
        ]

        for config_file in config_files:
            full_path = self.project_root / config_file
            if full_path.exists():
                print(f"   ✅ {config_file}")
            else:
                self.warnings.append(f"Optional config missing: {config_file}")

        return True

    def check_host_recommendations(self) -> None:
        """Provide host-specific recommendations."""
        print(f"💡 Platform-Specific Recommendations for {self.host_arch}:")

        if self.host_arch in ['x86_64', 'amd64']:
            print("   🖥️ AMD64 Host:")
            print("     • Excellent for multi-architecture development")
            print("     • Can build and test all target platforms")
            print("     • QEMU emulation handles ARM builds well")
            print("     • Use 'make build-multiarch' for complete testing")

        elif self.host_arch in ['aarch64', 'arm64']:
            print("   🎯 ARM64 Host:")
            print("     • Native ARM64 builds with excellent performance")
            print("     • AMD64 builds work via emulation")
            print("     • ARMv7 builds work via emulation")

            if self.host_os == 'Darwin':
                print("     🍎 Apple Silicon specific:")
                print("       - Ensure Docker Desktop uses ARM64 mode")
                print("       - Native performance for ARM64 builds")
                print("       - Excellent development platform for Harbor")
            else:
                print("     🐧 ARM64 Linux:")
                print("       - Great for ARM server/Pi 4 development")
                print("       - Test ARM optimizations natively")

        elif self.host_arch.startswith('arm'):
            print("   🥧 ARMv7 Host (Raspberry Pi 3?):")
            print("     • Native ARMv7 builds")
            print("     • Cross-compilation may be slow")
            print("     • Consider developing on faster machine")
            print("     • Great for testing ARMv7 constraints")

        else:
            print("   ❓ Unknown Host:")
            print("     • Using conservative defaults")
            print("     • AMD64 emulation should work")

    def validate_ci_setup(self) -> bool:
        """Validate CI/CD configuration for multi-arch."""
        print("🔄 Validating CI/CD Configuration...")

        ci_files = [
            '.github/workflows/ci-cd.yml',
            '.github/workflows/docker-build.yml',
            '.github/workflows/test.yml',
        ]

        for ci_file in ci_files:
            full_path = self.project_root / ci_file
            if full_path.exists():
                print(f"   ✅ {ci_file}")

                # Check if file contains multi-arch configuration
                with open(full_path, 'r') as f:
                    content = f.read()
                    if 'linux/arm64' in content and 'linux/arm/v7' in content:
                        print(f"     ✅ Multi-architecture support detected")
                    else:
                        self.warnings.append(f"{ci_file} may not support multi-arch")
            else:
                self.warnings.append(f"CI file missing: {ci_file}")

        return True

    def run_validation(self) -> bool:
        """Run complete validation suite."""
        print("🔍 Harbor Multi-Architecture Environment Validation")
        print("=" * 55)
        print("")

        print(f"🏠 Host Platform: {self.host_arch} ({self.host_os})")
        print("")

        # Run all validations
        validations = [
            self.validate_docker_setup,
            self.validate_qemu_setup,
            self.validate_project_structure,
            self.validate_platform_configs,
            self.validate_ci_setup,
        ]

        all_passed = True
        for validation in validations:
            try:
                if not validation():
                    all_passed = False
                print("")
            except Exception as e:
                self.issues.append(f"Validation error: {str(e)}")
                all_passed = False
                print("")

        # Show recommendations
        self.check_host_recommendations()
        print("")

        # Summary
        self.print_summary()

        return all_passed and len(self.issues) == 0

    def print_summary(self) -> None:
        """Print validation summary."""
        print("📋 Validation Summary")
        print("=" * 20)
        print("")

        if self.issues:
            print("❌ Critical Issues:")
            for issue in self.issues:
                print(f"   • {issue}")
            print("")

        if self.warnings:
            print("⚠️ Warnings:")
            for warning in self.warnings:
                print(f"   • {warning}")
            print("")

        if not self.issues and not self.warnings:
            print("✅ All validations passed!")
            print("🎉 Multi-architecture development environment ready!")
        elif not self.issues:
            print("✅ No critical issues found")
            print("💡 Address warnings for optimal experience")
        else:
            print("❌ Critical issues must be resolved")
            print("🔧 Fix issues above before proceeding")

        print("")
        print("🚀 Quick Start Commands:")
        print("   make dev-multiarch-setup       # Setup multi-arch environment")
        print("   make build-multiarch           # Build all platforms")
        print("   make test-multiarch            # Test all platforms")
        print("   make platform-detect           # Show platform recommendations")


def main() -> None:
    """Main entry point."""
    validator = MultiArchValidator()
    success = validator.run_validation()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()