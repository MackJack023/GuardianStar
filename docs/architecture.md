# GuardianStar Architecture

The following diagram explains the complete end-to-end system in one view.

```mermaid
flowchart LR
  subgraph C["Client App (Android)"]
    C1["MainActivity\nPermission + Server Config"]
    C2["LocationTrackingService\nGPS + Geofence"]
    C3["LocationApi\nPOST /location, /alert\nGET /safe-zone"]
    C1 --> C2 --> C3
  end

  subgraph B["Backend API (FastAPI)"]
    B1["REST API\n/api/*"]
    B2["Domain Layer\nDevice + Location + Alert + SafeZone"]
    B3["SQLAlchemy ORM"]
    B4["SQLite\nguardianstar.db"]
    B5["Realtime Push\nWS /api/ws/alerts"]
    B1 --> B2 --> B3 --> B4
    B1 --> B5
  end

  subgraph M["Monitor App (Android)"]
    M1["MonitorActivity\nDevice Switch + Dashboard"]
    M2["MonitorApi\n/devices + per-device query"]
    M3["AlertPushClient\nWebSocket + local notifications"]
    M1 --> M2
    M1 --> M3
  end

  C3 -- "Upload location + geofence alerts" --> B1
  M2 -- "Read devices/latest/history/alerts\nSet or clear safe-zone" --> B1
  B5 -- "Push EXIT/ENTER alerts" --> M3
  B1 -- "Safe-zone config by deviceId" --> C3
```

## Runtime Components

- API framework: FastAPI + Uvicorn
- Persistence: SQLAlchemy ORM + SQLite
- Alert push channel: backend WebSocket + Monitor local notification
- Legacy migration: `server_state.json` auto-import on first startup

## Data Model

- `devices`: unique `deviceId` and lifecycle timestamps
- `locations`: geolocation history per device
- `alerts`: geofence and safety events
- `safe_zones`: active safe-zone settings per device
- `push_tokens`: reserved registry for external push provider integration
