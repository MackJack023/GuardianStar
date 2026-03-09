# GuardianStar

[![Android CI](https://github.com/MackJack023/GuardianStar/actions/workflows/android-ci.yml/badge.svg)](https://github.com/MackJack023/GuardianStar/actions/workflows/android-ci.yml)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](./docs/releases/v1.0.0.md)
[![Platform](https://img.shields.io/badge/platform-Android%20%2B%20Python-3c82f6)](./Client/server/server.py)

GuardianStar is a multi-device family safety prototype built around two Android apps and a lightweight Python backend.

- `Client`: the protected child-side app
- `Monitor`: the guardian-side monitoring app
- `Client/server`: the backend that stores locations, alerts, and safe-zone state

## What It Does

GuardianStar already supports a full working loop:

1. `Client` uploads location and alert events with its own `deviceId`
2. The backend stores data per device
3. `Monitor` loads the tracked device list and switches between children
4. Guardians can assign or remove a safe zone for a specific device
5. `Client` syncs the safe zone for its own `deviceId` and registers Android Geofence rules
6. Enter and exit events are reported back to the backend and shown in `Monitor`

## Project Layout

### Android Apps

- [Client/src/main/java/com/example/guardianstar/ui/MainActivity.kt](./Client/src/main/java/com/example/guardianstar/ui/MainActivity.kt)
  Child-side UI for permissions, service control, and backend configuration.
- [Client/src/main/java/com/example/guardianstar/service/LocationTrackingService.kt](./Client/src/main/java/com/example/guardianstar/service/LocationTrackingService.kt)
  Foreground location service with safe-zone sync and geofence registration.
- [Monitor/src/main/java/com/example/guardianstar/monitor/MonitorActivity.kt](./Monitor/src/main/java/com/example/guardianstar/monitor/MonitorActivity.kt)
  Guardian-side UI with device switching, map display, alert display, and safe-zone actions.
- [Monitor/src/main/java/com/example/guardianstar/monitor/network/MonitorApi.kt](./Monitor/src/main/java/com/example/guardianstar/monitor/network/MonitorApi.kt)
  Multi-device API contract for monitor-side queries.

### Backend

- [Client/server/server.py](./Client/server/server.py)
  Lightweight multi-device HTTP backend.
- [Client/server/test_server.py](./Client/server/test_server.py)
  Automated tests for health, per-device isolation, and safe-zone behavior.
- [compose.yaml](./compose.yaml)
  Docker Compose entry point for the backend.

## API Surface

### Read

- `GET /api/health`
- `GET /api/devices`
- `GET /api/latest?deviceId=...`
- `GET /api/history?deviceId=...`
- `GET /api/alerts?deviceId=...`
- `GET /api/safe-zone?deviceId=...`

### Write

- `POST /api/location`
- `POST /api/alert`
- `POST /api/safe-zone`
- `DELETE /api/safe-zone?deviceId=...`

## Quick Start

### Run the backend locally

```powershell
cd Client\server
python server.py
```

### Or run the backend with Docker

```powershell
docker compose up --build
```

### Build both Android apps

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

APK outputs:

- `Client/build/outputs/apk/debug/GuardianStar-debug.apk`
- `Monitor/build/outputs/apk/debug/monitor-debug.apk`

### Install

```powershell
adb install -r Client\build\outputs\apk\debug\GuardianStar-debug.apk
adb install -r Monitor\build\outputs\apk\debug\monitor-debug.apk
```

## Runtime Configuration

### Client

Default backend URL:

```text
http://10.0.2.2:8080/
```

For physical devices, update the server address from `Profile -> Server Settings` to your machine's LAN IP.

### Monitor

Copy [Monitor/local.properties.example](./Monitor/local.properties.example) to `Monitor/local.properties` and customize it:

```properties
monitor.baseUrl=http://10.0.2.2:8080/
amap.webApiKey=your-amap-web-api-key
```

## Validation

### Backend tests

```powershell
python -m unittest discover -s .\Client\server -p "test_*.py"
```

### Android build

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

Both commands were run successfully in this repository before publishing.

## CI / CD

GitHub Actions is configured in [android-ci.yml](./.github/workflows/android-ci.yml) to:

- run backend unit tests
- build both Android debug APKs
- upload APK artifacts for every push, pull request, and manual run
- create a GitHub Release with APK assets when a `v*` tag is pushed

## Release Notes

- [v1.0.0](./docs/releases/v1.0.0.md)

## Current Limitations

GuardianStar is now good for demos and internal prototypes, but it is not yet a production system. It still lacks:

- authentication and account binding
- a real database layer
- push notifications
- production-grade backend framework and auth middleware
- secure secret management for map keys

## License

See [LICENSE](./LICENSE).
