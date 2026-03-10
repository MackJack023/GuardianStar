# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog, and this project uses semantic versioning.

## [Unreleased]

## [1.0.1] - 2026-03-10

### Added

- Open-source style repository presentation assets and governance docs
- Unified real-device style screenshot set for README
- Architecture overview document (`docs/architecture.md`)
- Deployment guide (`docs/DEPLOYMENT.md`)
- Contributing, security, and code of conduct policies
- Issue templates and pull request template
- Dependabot configuration for GitHub Actions and Gradle
- Backend validation tests for invalid location payload and safe-zone radius

### Changed

- Upgraded repository homepage README to production-style open-source format
- Hardened backend input validation for location and safe-zone APIs
- Switched backend runtime server to `ThreadingHTTPServer`
- Aligned Android Gradle plugin versions to `8.2.2`

## [1.0.0] - 2026-03-09

### Added

- First release-tagged, multi-device demoable GuardianStar version
- Device-aware backend model keyed by `deviceId`
- Monitor-side device switching and per-device safe-zone controls
- Client-side safe-zone sync with geofence registration
- Docker packaging for backend
- GitHub Actions CI for backend tests and APK builds
- Release notes and tag-based APK release workflow
