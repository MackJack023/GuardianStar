# Deployment Guide

This document provides practical deployment paths for GuardianStar.

## 1. Local Development Deployment

### Backend

```bash
cd Client/server
python server.py
```

Default backend URL: `http://localhost:8080`

### Android Apps

```bash
cd Client
./gradlew --no-daemon clean assembleDebug :monitor:assembleDebug
```

Install APKs:

```bash
adb install -r Client/build/outputs/apk/debug/GuardianStar-debug.apk
adb install -r Monitor/build/outputs/apk/debug/monitor-debug.apk
```

## 2. Docker Deployment (Backend)

```bash
docker compose up --build -d
```

Stop:

```bash
docker compose down
```

## 3. Environment Variables

Backend supports:

- `PORT` (default `8080`)
- `GUARDIANSTAR_STATE_FILE` (default `Client/server/server_state.json`)

Example:

```bash
PORT=8080 GUARDIANSTAR_STATE_FILE=/data/server_state.json python server.py
```

## 4. Production Hardening Checklist

- Put backend behind a reverse proxy (Nginx/Caddy)
- Add API authentication and request rate limiting
- Move persistence to SQLite/PostgreSQL
- Back up persistent state on schedule
- Store map keys and secrets outside repository files
- Enable HTTPS termination for all client/backend traffic

