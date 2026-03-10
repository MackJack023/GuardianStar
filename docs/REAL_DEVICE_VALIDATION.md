# Real Device Validation Checklist

This checklist verifies Java 17 builds, backend database persistence, and real-time push notifications on physical Android devices.

## Test Topology

- Device A: install `GuardianStar-debug.apk` (Client)
- Device B: install `monitor-debug.apk` (Monitor)
- Backend: run on a LAN host reachable by both devices

## 1. Prepare Backend

```bash
cd Client/server
pip install -r requirements.txt
python server.py
```

Expected:

- `GET /api/health` returns `status=ok`
- A SQLite file `guardianstar.db` is created

## 2. Build + Install APKs

```bash
cd Client
./gradlew --no-daemon clean assembleDebug :monitor:assembleDebug
adb install -r Client/build/outputs/apk/debug/GuardianStar-debug.apk
adb install -r Monitor/build/outputs/apk/debug/monitor-debug.apk
```

Expected:

- Both APKs install successfully
- No Java target mismatch errors during build (Java 17 target)

## 3. Configure Real Backend Address

On both Android apps, use LAN backend URL:

- Example: `http://192.168.1.20:8080/`

In Monitor module, this can also be preconfigured with:

```properties
monitor.baseUrl=http://192.168.1.20:8080/
```

## 4. Client Device (A) Validation

1. Grant fine/coarse/background location.
2. Start protection service from Home.
3. Keep app in background for at least 3 location upload cycles.

Expected:

- Foreground notification is shown for active protection
- Backend receives `/api/location` payloads for the device

## 5. Monitor Device (B) Validation

1. Open Monitor app and grant notification permission on Android 13+.
2. Confirm device appears in tracked list.
3. Set safe zone from current location.

Expected:

- Device status updates every refresh cycle
- Safe zone is visible on map
- Top bar shows `Push On` after websocket connection

## 6. Geofence + Push Validation

1. Move Device A outside safe-zone radius.
2. Trigger geofence `EXIT`.
3. Return Device A inside zone to trigger `ENTER`.

Expected:

- Backend stores alerts (`GET /api/alerts`)
- Monitor receives websocket alert payloads
- Monitor shows local notification for EXIT/ENTER

## 7. Database Persistence Validation

1. Stop backend.
2. Restart backend.
3. Open Monitor and reload same device.

Expected:

- Last location, history, safe zone, and alerts are preserved
- Data remains available from SQLite without re-upload

## 8. Pass Criteria

- Backend health stable for 30+ minutes
- Client uploads continue in background
- Monitor push alerts arrive in near real-time
- Data survives backend restart
