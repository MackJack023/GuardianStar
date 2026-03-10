# Deployment Guide

This document provides practical deployment paths for GuardianStar.

## 1. Local Development Deployment

### Backend

```bash
cd Client/server
pip install -r requirements.txt
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
- `GUARDIANSTAR_DATABASE_URL` (default `sqlite:///Client/server/guardianstar.db`)
- `GUARDIANSTAR_LEGACY_STATE_FILE` (default `Client/server/server_state.json`)
- `GUARDIANSTAR_ALERT_WEBHOOK_URL` (optional webhook sink for alert fan-out)
- `GUARDIANSTAR_CORS_ORIGINS` (comma separated origins, default `*`)

Example:

```bash
PORT=8080 \
GUARDIANSTAR_DATABASE_URL=sqlite:///./guardianstar.db \
GUARDIANSTAR_LEGACY_STATE_FILE=./server_state.json \
python server.py
```

## 4. Production Hardening Checklist

- Put backend behind a reverse proxy (Nginx/Caddy)
- Enable TLS for all app-backend traffic
- Restrict `GUARDIANSTAR_CORS_ORIGINS` for production domains
- Rotate webhook credentials and avoid hardcoding secrets
- Back up SQLite file (or migrate to PostgreSQL profile)
- Add API authentication + guardian-child ownership authorization
