# Contributing to GuardianStar

Thanks for your interest in improving GuardianStar.

## Development Setup

1. Fork the repository and create a feature branch from `main`.
2. Install requirements:
   - Android Studio (or Android SDK + JDK 17)
   - Python 3.12+
   - Docker (optional, for backend container run)
3. Build and test locally:
   - `python -m unittest discover -s .\Client\server -p "test_*.py"`
   - `cd Client`
   - `.\gradlew.bat --no-daemon clean assembleDebug :monitor:assembleDebug`

## Pull Request Checklist

- Keep PR scope focused on one feature or fix.
- Add or update tests for backend behavior changes.
- Ensure the Android build passes.
- Update docs when API, configuration, or setup changes.
- Use clear commit messages (`feat:`, `fix:`, `docs:`, `build:`).

## Coding Guidelines

- Keep APIs backward compatible when possible.
- Avoid committing secrets (API keys, tokens, local config files).
- Prefer small, reviewable changes over large mixed refactors.
- Keep user-facing text clear and consistent.

## Reporting Issues

When filing an issue, include:

- expected behavior
- actual behavior
- reproduction steps
- environment details (OS, Android version, app version)

## Community

By participating, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

