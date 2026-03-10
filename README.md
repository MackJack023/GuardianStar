# GuardianStar

[![Android CI](https://github.com/MackJack023/GuardianStar/actions/workflows/android-ci.yml/badge.svg)](https://github.com/MackJack023/GuardianStar/actions/workflows/android-ci.yml)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](./docs/releases/v1.0.0.md)
[![Platform](https://img.shields.io/badge/platform-Android%20%2B%20Python-3c82f6)](./Client/server/server.py)

GuardianStar is a **multi-device family safety prototype** consisting of two Android applications and a lightweight Python backend.

It demonstrates a full **child tracking and guardian monitoring workflow**, including location reporting, alerts, safe-zone configuration, and geofence event detection.

## Key Features

- Child-side Android tracking app (`Client`)
- Guardian monitoring app (`Monitor`)
- Multi-device backend using `deviceId`
- Real-time location reporting
- Safe-zone assignment and synchronization
- Android geofence detection for entry and exit events
- REST API backend with Docker support
- CI pipeline with automated builds and tests

---

# System Overview

GuardianStar is composed of three main components:

| Component | Description |
|---|---|
| Client | Android app installed on the child's device |
| Monitor | Android app used by guardians to track devices |
| Backend | Python service that stores locations, alerts, and safe-zone data |

### Workflow

1. The **Client app** uploads location and alert events using its `deviceId`
2. The **backend** stores all data separately per device
3. The **Monitor app** retrieves device lists and switches between children
4. Guardians can assign or remove a **safe zone**
5. The **Client app** synchronizes safe-zone data and registers Android geofence rules
6. Entry/exit events are sent back to the backend and displayed in the Monitor app

This creates a complete **end-to-end safety monitoring loop**.

---

# Project Structure

## Android Applications

### Client (Child Device)

Key components:

- `MainActivity.kt`  
  Handles permissions, service control, and backend configuration.

- `LocationTrackingService.kt`  
  Foreground location service responsible for:
  - location updates
  - safe-zone synchronization
  - geofence registration

### Monitor (Guardian Device)

Key components:

- `MonitorActivity.kt`  
  Provides guardian interface for:
  - device switching
  - map display
  - alert monitoring
  - safe-zone management

- `MonitorApi.kt`  
  Defines network API for multi-device queries.

---

## Backend

Located in:


Main files:

- `server.py`  
  Lightweight HTTP backend responsible for device data storage.

- `test_server.py`  
  Unit tests covering:
  - health endpoint
  - device isolation
  - safe-zone behavior

- `compose.yaml`  
  Docker Compose configuration for backend deployment.

---

# API Overview

## Read Endpoints

- `GET /api/health`
- `GET /api/devices`
- `GET /api/latest?deviceId=...`
- `GET /api/history?deviceId=...`
- `GET /api/alerts?deviceId=...`
- `GET /api/safe-zone?deviceId=...`

## Write Endpoints

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
