from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import asyncio
import datetime as dt
import hashlib
import json
import os
import sys

from fastapi import Depends, FastAPI, HTTPException, Request as FastAPIRequest, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, desc, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
import uvicorn


MAX_HISTORY = 200
MAX_ALERTS = 200


def now_timestamp_ms() -> int:
    return int(dt.datetime.now().timestamp() * 1000)


def format_timestamp(timestamp_ms: int) -> str:
    return dt.datetime.fromtimestamp(timestamp_ms / 1000.0).strftime("%Y-%m-%d %H:%M:%S")


def anonymize_device_id(device_id: str) -> str:
    normalized = str(device_id or "").strip()
    if not normalized:
        return "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"id:{digest[:10]}"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


@dataclass(slots=True)
class Settings:
    port: int
    database_url: str
    legacy_state_file: Path
    alert_webhook_url: str | None
    cors_origins: list[str]


def load_settings(
    *,
    database_url: str | None = None,
    legacy_state_file: Path | None = None,
    alert_webhook_url: str | None = None,
) -> Settings:
    default_db_path = Path(__file__).with_name("guardianstar.db").as_posix()
    resolved_database_url = database_url or os.getenv("GUARDIANSTAR_DATABASE_URL", f"sqlite:///{default_db_path}")
    resolved_legacy_state_file = legacy_state_file or Path(
        os.getenv(
            "GUARDIANSTAR_LEGACY_STATE_FILE",
            os.getenv("GUARDIANSTAR_STATE_FILE", str(Path(__file__).with_name("server_state.json"))),
        )
    )
    resolved_alert_webhook_url = alert_webhook_url if alert_webhook_url is not None else os.getenv(
        "GUARDIANSTAR_ALERT_WEBHOOK_URL", ""
    ).strip()
    cors_origins_raw = os.getenv("GUARDIANSTAR_CORS_ORIGINS", "*")
    cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()] or ["*"]
    return Settings(
        port=int(os.getenv("PORT", "8080")),
        database_url=resolved_database_url,
        legacy_state_file=resolved_legacy_state_file,
        alert_webhook_url=resolved_alert_webhook_url or None,
        cors_origins=cors_origins,
    )


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    locations: Mapped[list["Location"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="Location.timestamp_ms",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(Alert.timestamp_ms)",
    )
    safe_zone: Mapped["SafeZone | None"] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        uselist=False,
    )
    push_tokens: Mapped[list["PushToken"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_fk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    time_str: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="locations")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_fk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    time_str: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="alerts")


class SafeZone(Base):
    __tablename__ = "safe_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_fk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=now_timestamp_ms)

    device: Mapped["Device"] = relationship(back_populates="safe_zone")


class PushToken(Base):
    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="android", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    device_fk: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)

    device: Mapped["Device | None"] = relationship(back_populates="push_tokens")


class LocationIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    deviceId: str = Field(min_length=1, max_length=128)
    latitude: float
    longitude: float
    timestamp: int | None = None


class AlertIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    deviceId: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    timestamp: int | None = None


class SafeZoneIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceId: str = Field(min_length=1, max_length=128)
    latitude: float
    longitude: float
    radius: float = Field(gt=0)


class PushRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=512)
    deviceId: str | None = Field(default=None, max_length=128)
    platform: str = Field(default="android", max_length=32)


def _extra_payload(payload_json: str | None) -> dict[str, Any]:
    if not payload_json:
        return {}
    try:
        loaded = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def serialize_location(location: Location, device_id: str) -> dict[str, Any]:
    payload = _extra_payload(location.payload_json)
    payload.update(
        {
            "deviceId": device_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": location.timestamp_ms,
            "time_str": location.time_str,
        }
    )
    return payload


def serialize_alert(alert: Alert, device_id: str) -> dict[str, Any]:
    payload = _extra_payload(alert.payload_json)
    payload.update(
        {
            "deviceId": device_id,
            "type": alert.alert_type,
            "timestamp": alert.timestamp_ms,
            "time_str": alert.time_str,
        }
    )
    return payload


def serialize_safe_zone(safe_zone: SafeZone | None, *, device_id: str | None = None) -> dict[str, Any]:
    if not safe_zone:
        return {"active": False} if not device_id else {"active": False, "deviceId": device_id}

    payload: dict[str, Any] = {
        "active": bool(safe_zone.active),
        "deviceId": device_id,
        "updatedAt": safe_zone.updated_at_ms,
    }
    if safe_zone.active:
        payload.update(
            {
                "latitude": safe_zone.latitude,
                "longitude": safe_zone.longitude,
                "radius": safe_zone.radius,
            }
        )
    return payload


def get_or_create_device(session: Session, device_id: str) -> Device:
    device = session.scalar(select(Device).where(Device.device_id == device_id))
    if device:
        return device
    device = Device(device_id=device_id)
    session.add(device)
    session.flush()
    return device


def latest_location_for_device(session: Session, device: Device) -> Location | None:
    return session.scalar(
        select(Location).where(Location.device_fk == device.id).order_by(desc(Location.timestamp_ms), desc(Location.id)).limit(1)
    )


def resolve_device(session: Session, device_id: str | None) -> Device | None:
    if device_id:
        return session.scalar(select(Device).where(Device.device_id == device_id))

    latest_device_subquery = (
        select(
            Location.device_fk.label("device_fk"),
            func.max(Location.timestamp_ms).label("max_timestamp"),
        )
        .group_by(Location.device_fk)
        .subquery()
    )
    latest = session.execute(
        select(Device)
        .outerjoin(latest_device_subquery, latest_device_subquery.c.device_fk == Device.id)
        .order_by(desc(func.coalesce(latest_device_subquery.c.max_timestamp, 0)), desc(Device.updated_at))
        .limit(1)
    ).scalar_one_or_none()
    return latest


def sorted_devices(session: Session) -> list[Device]:
    latest_device_subquery = (
        select(
            Location.device_fk.label("device_fk"),
            func.max(Location.timestamp_ms).label("max_timestamp"),
        )
        .group_by(Location.device_fk)
        .subquery()
    )
    rows = session.execute(
        select(Device)
        .outerjoin(latest_device_subquery, latest_device_subquery.c.device_fk == Device.id)
        .order_by(desc(func.coalesce(latest_device_subquery.c.max_timestamp, 0)), desc(Device.updated_at))
    )
    return [row[0] for row in rows]


def device_summary(session: Session, device: Device) -> dict[str, Any]:
    latest = latest_location_for_device(session, device)
    safe_zone = session.scalar(select(SafeZone).where(SafeZone.device_fk == device.id))
    return {
        "deviceId": device.device_id,
        "lastUpdatedAt": latest.timestamp_ms if latest else None,
        "lastUpdatedText": latest.time_str if latest else None,
        "latitude": latest.latitude if latest else None,
        "longitude": latest.longitude if latest else None,
        "safeZoneActive": bool(safe_zone.active) if safe_zone else False,
    }


def empty_device_state(device_id: str) -> dict[str, Any]:
    return {
        "deviceId": device_id,
        "last_location": {},
        "location_history": [],
        "alerts": [],
        "safe_zone": {"active": False, "deviceId": device_id},
    }


def normalize_device_state(device_id: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    device_state = empty_device_state(device_id)
    if not raw:
        return device_state

    device_state["last_location"] = raw.get("last_location", {}) or {}
    device_state["location_history"] = raw.get("location_history", [])[-MAX_HISTORY:]
    device_state["alerts"] = raw.get("alerts", [])[:MAX_ALERTS]

    safe_zone = raw.get("safe_zone", {}) or {}
    device_state["safe_zone"] = {
        "active": bool(safe_zone.get("active", False)),
        "deviceId": safe_zone.get("deviceId", device_id),
        "latitude": safe_zone.get("latitude"),
        "longitude": safe_zone.get("longitude"),
        "radius": safe_zone.get("radius"),
        "updatedAt": safe_zone.get("updatedAt"),
    }
    return device_state


def migrate_legacy_raw_state(raw: dict[str, Any]) -> dict[str, Any]:
    devices: dict[str, Any] = {}

    if isinstance(raw.get("devices"), dict):
        for raw_device_id, raw_device_state in raw["devices"].items():
            device_id = str((raw_device_state or {}).get("deviceId") or raw_device_id)
            devices[device_id] = normalize_device_state(device_id, raw_device_state)
        return {"devices": devices}

    for location in raw.get("location_history", []):
        device_id = str(location.get("deviceId") or "unknown_device")
        state = devices.setdefault(device_id, empty_device_state(device_id))
        state["location_history"].append(location)

    for alert in raw.get("alerts", []):
        device_id = str(alert.get("deviceId") or "unknown_device")
        state = devices.setdefault(device_id, empty_device_state(device_id))
        state["alerts"].append(alert)

    if raw.get("last_location"):
        location = raw["last_location"]
        device_id = str(location.get("deviceId") or "unknown_device")
        state = devices.setdefault(device_id, empty_device_state(device_id))
        state["last_location"] = location

    if raw.get("safe_zone"):
        candidate_device_id = "unknown_device"
        last_location = raw.get("last_location", {})
        if last_location.get("deviceId"):
            candidate_device_id = str(last_location["deviceId"])
        elif devices:
            candidate_device_id = next(iter(devices))

        state = devices.setdefault(candidate_device_id, empty_device_state(candidate_device_id))
        safe_zone = raw["safe_zone"]
        state["safe_zone"] = {
            "active": bool(safe_zone.get("active", False)),
            "deviceId": candidate_device_id,
            "latitude": safe_zone.get("latitude"),
            "longitude": safe_zone.get("longitude"),
            "radius": safe_zone.get("radius"),
            "updatedAt": safe_zone.get("updatedAt"),
        }

    return {
        "devices": {
            device_id: normalize_device_state(device_id, device_state)
            for device_id, device_state in devices.items()
        }
    }


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def import_legacy_state_if_needed(session: Session, state_file: Path) -> None:
    existing_devices = session.scalar(select(func.count()).select_from(Device)) or 0
    if existing_devices > 0 or not state_file.exists():
        return

    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return

    normalized = migrate_legacy_raw_state(raw)
    imported_locations = 0
    imported_alerts = 0
    imported_devices = 0

    for device_id, device_state in normalized.get("devices", {}).items():
        device = get_or_create_device(session, str(device_id))
        imported_devices += 1

        history = device_state.get("location_history", []) or []
        if not history and device_state.get("last_location"):
            history = [device_state["last_location"]]

        for location in history:
            timestamp = _safe_int(location.get("timestamp"), now_timestamp_ms())
            latitude = _safe_float(location.get("latitude"), 0.0)
            longitude = _safe_float(location.get("longitude"), 0.0)
            payload = dict(location)
            payload.update(
                {
                    "deviceId": device.device_id,
                    "timestamp": timestamp,
                    "latitude": latitude,
                    "longitude": longitude,
                    "time_str": payload.get("time_str") or format_timestamp(timestamp),
                }
            )
            session.add(
                Location(
                    device_fk=device.id,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_ms=timestamp,
                    time_str=payload["time_str"],
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            )
            imported_locations += 1

        for alert in device_state.get("alerts", []) or []:
            timestamp = _safe_int(alert.get("timestamp"), now_timestamp_ms())
            alert_type = str(alert.get("type") or "UNKNOWN")
            payload = dict(alert)
            payload.update(
                {
                    "deviceId": device.device_id,
                    "type": alert_type,
                    "timestamp": timestamp,
                    "time_str": payload.get("time_str") or format_timestamp(timestamp),
                }
            )
            session.add(
                Alert(
                    device_fk=device.id,
                    alert_type=alert_type,
                    timestamp_ms=timestamp,
                    time_str=payload["time_str"],
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            )
            imported_alerts += 1

        safe_zone = device_state.get("safe_zone") or {}
        if safe_zone.get("active"):
            session.add(
                SafeZone(
                    device_fk=device.id,
                    active=True,
                    latitude=_safe_float(safe_zone.get("latitude"), 0.0),
                    longitude=_safe_float(safe_zone.get("longitude"), 0.0),
                    radius=_safe_float(safe_zone.get("radius"), 100.0),
                    updated_at_ms=_safe_int(safe_zone.get("updatedAt"), now_timestamp_ms()),
                )
            )
        else:
            session.add(
                SafeZone(
                    device_fk=device.id,
                    active=False,
                    updated_at_ms=_safe_int(safe_zone.get("updatedAt"), now_timestamp_ms()),
                )
            )

    session.commit()
    print(
        "[migration] imported legacy state "
        f"devices={imported_devices} locations={imported_locations} alerts={imported_alerts}",
        flush=True,
    )


class AlertBroadcaster:
    def __init__(self) -> None:
        self._connections: list[tuple[WebSocket, str | None]] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, device_id: str | None) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append((websocket, device_id))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections = [(ws, target_device) for ws, target_device in self._connections if ws is not websocket]

    async def broadcast(self, alert_payload: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)

        stale_connections: list[WebSocket] = []
        for websocket, target_device in connections:
            if target_device and alert_payload.get("deviceId") != target_device:
                continue
            try:
                await websocket.send_json(alert_payload)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)


def build_dashboard_html(device_count: int, latest_device_summary: dict[str, Any] | None) -> str:
    if not latest_device_summary:
        status_html = "<p>Waiting for tracked devices...</p>"
        location_summary = "No location available"
    else:
        latitude = latest_device_summary.get("latitude")
        longitude = latest_device_summary.get("longitude")
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            location_summary = f"{float(latitude):.5f}, {float(longitude):.5f}"
        else:
            location_summary = "Unknown"

        status_html = f"""
            <div class="info-item"><span class="label">Device:</span><span class="value">{str(latest_device_summary['deviceId'])[-6:].upper()}</span></div>
            <div class="info-item"><span class="label">Updated:</span><span class="value">{latest_device_summary.get('lastUpdatedText') or '-'}</span></div>
            <div class="info-item"><span class="label">Location:</span><span class="value">{location_summary}</span></div>
            <div class="info-item"><span class="label">Safe Zone:</span><span class="value">{'Active' if latest_device_summary.get('safeZoneActive') else 'Not configured'}</span></div>
            <div class="info-item"><span class="label">Devices:</span><span class="value">{device_count}</span></div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="10">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GuardianStar Backend</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background: #f5f7fa;
                color: #243447;
            }}
            header {{
                background: #4a90e2;
                color: white;
                padding: 16px;
                text-align: center;
            }}
            main {{
                padding: 24px;
                display: grid;
                gap: 16px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 6px 18px rgba(18, 38, 63, 0.08);
            }}
            .title {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 8px;
            }}
            .info-item {{
                margin-bottom: 8px;
                font-size: 15px;
            }}
            .label {{
                color: #637083;
                margin-right: 10px;
            }}
            .value {{
                font-weight: bold;
                color: #243447;
            }}
        </style>
    </head>
    <body>
        <header>
            <h2 style="margin:0">GuardianStar Backend</h2>
        </header>
        <main>
            <div class="card">
                <div class="title">Latest tracked location</div>
                <div>{location_summary}</div>
            </div>
            <div class="card">
                <div class="title">System status</div>
                {status_html}
            </div>
        </main>
    </body>
    </html>
    """


def post_alert_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            if response.status >= 400:
                print(f"[push] webhook failed status={response.status}", flush=True)
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"[push] webhook error={error}", flush=True)


def create_app(
    *,
    database_url: str | None = None,
    legacy_state_file: Path | None = None,
    alert_webhook_url: str | None = None,
) -> FastAPI:
    settings = load_settings(
        database_url=database_url,
        legacy_state_file=legacy_state_file,
        alert_webhook_url=alert_webhook_url,
    )

    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    broadcaster = AlertBroadcaster()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(bind=engine)
        with session_factory() as session:
            import_legacy_state_if_needed(session, settings.legacy_state_file)

        print("GuardianStar backend started", flush=True)
        print(f"Database: {settings.database_url}", flush=True)
        print(f"Health: http://localhost:{settings.port}/api/health", flush=True)
        print(f"Devices: http://localhost:{settings.port}/api/devices", flush=True)
        print(f"Latest location: http://localhost:{settings.port}/api/latest", flush=True)
        print(f"Alert stream: ws://localhost:{settings.port}/api/ws/alerts", flush=True)
        print(f"Monitor page: http://localhost:{settings.port}/", flush=True)
        yield
        engine.dispose()

    app = FastAPI(
        title="GuardianStar Backend",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=512)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_response_security_headers(
        request: FastAPIRequest,
        call_next,
    ):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    def get_session() -> Session:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @app.get("/", response_class=HTMLResponse)
    def index(session: Session = Depends(get_session)) -> str:
        devices = sorted_devices(session)
        latest_summary = device_summary(session, devices[0]) if devices else None
        return build_dashboard_html(device_count=len(devices), latest_device_summary=latest_summary)

    @app.get("/api/health")
    def health_check() -> dict[str, Any]:
        return {
            "status": "ok",
            "time": format_timestamp(now_timestamp_ms()),
            "database": "ok",
            "push": "websocket",
            "framework": "fastapi",
        }

    @app.get("/api/devices")
    def list_devices(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
        return [device_summary(session, device) for device in sorted_devices(session)]

    @app.get("/api/latest")
    def latest_location(
        deviceId: str | None = None,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        device = resolve_device(session, deviceId)
        if not device:
            return {}
        latest = latest_location_for_device(session, device)
        return serialize_location(latest, device.device_id) if latest else {}

    @app.get("/api/history")
    def location_history(
        deviceId: str | None = None,
        session: Session = Depends(get_session),
    ) -> list[dict[str, Any]]:
        device = resolve_device(session, deviceId)
        if not device:
            return []
        rows = session.scalars(
            select(Location)
            .where(Location.device_fk == device.id)
            .order_by(desc(Location.timestamp_ms), desc(Location.id))
            .limit(MAX_HISTORY)
        ).all()
        rows = list(reversed(rows))
        return [serialize_location(location, device.device_id) for location in rows]

    @app.get("/api/alerts")
    def alerts(
        deviceId: str | None = None,
        session: Session = Depends(get_session),
    ) -> list[dict[str, Any]]:
        device = resolve_device(session, deviceId)
        if not device:
            return []
        rows = session.scalars(
            select(Alert).where(Alert.device_fk == device.id).order_by(desc(Alert.timestamp_ms), desc(Alert.id)).limit(MAX_ALERTS)
        ).all()
        return [serialize_alert(alert_row, device.device_id) for alert_row in rows]

    @app.get("/api/safe-zone")
    def safe_zone(
        deviceId: str | None = None,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        device = resolve_device(session, deviceId)
        if not device:
            return {"active": False}
        zone = session.scalar(select(SafeZone).where(SafeZone.device_fk == device.id))
        return serialize_safe_zone(zone, device_id=device.device_id)

    @app.post("/api/location")
    def post_location(payload: LocationIn, session: Session = Depends(get_session)) -> dict[str, str]:
        device = get_or_create_device(session, payload.deviceId.strip())
        timestamp = payload.timestamp if payload.timestamp is not None else now_timestamp_ms()
        latitude = float(payload.latitude)
        longitude = float(payload.longitude)

        data = payload.model_dump()
        data.update(
            {
                "deviceId": device.device_id,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
                "time_str": format_timestamp(timestamp),
            }
        )

        session.add(
            Location(
                device_fk=device.id,
                latitude=latitude,
                longitude=longitude,
                timestamp_ms=timestamp,
                time_str=data["time_str"],
                payload_json=json.dumps(data, ensure_ascii=False),
            )
        )
        device.updated_at = utc_now()
        session.commit()

        print(
            f"[location] device={anonymize_device_id(device.device_id)} time={data['time_str']}",
            flush=True,
        )
        return {"status": "success"}

    @app.post("/api/alert")
    async def post_alert(payload: AlertIn, session: Session = Depends(get_session)) -> dict[str, str]:
        device = get_or_create_device(session, payload.deviceId.strip())
        timestamp = payload.timestamp if payload.timestamp is not None else now_timestamp_ms()
        alert_type = payload.type.strip().upper()

        data = payload.model_dump()
        data.update(
            {
                "deviceId": device.device_id,
                "type": alert_type,
                "timestamp": timestamp,
                "time_str": format_timestamp(timestamp),
            }
        )

        alert_row = Alert(
            device_fk=device.id,
            alert_type=alert_type,
            timestamp_ms=timestamp,
            time_str=data["time_str"],
            payload_json=json.dumps(data, ensure_ascii=False),
        )
        session.add(alert_row)
        device.updated_at = utc_now()
        session.commit()
        session.refresh(alert_row)

        alert_payload = serialize_alert(alert_row, device.device_id)
        await broadcaster.broadcast(alert_payload)
        if settings.alert_webhook_url:
            asyncio.create_task(asyncio.to_thread(post_alert_webhook, settings.alert_webhook_url, alert_payload))

        print(
            "[alert] "
            f"device={anonymize_device_id(device.device_id)} "
            f"time={data['time_str']} type={alert_type}",
            flush=True,
        )
        return {"status": "success"}

    @app.post("/api/safe-zone")
    def set_safe_zone(payload: SafeZoneIn, session: Session = Depends(get_session)) -> dict[str, Any]:
        device = get_or_create_device(session, payload.deviceId.strip())
        zone = session.scalar(select(SafeZone).where(SafeZone.device_fk == device.id))
        if not zone:
            zone = SafeZone(device_fk=device.id)
            session.add(zone)

        zone.active = True
        zone.latitude = float(payload.latitude)
        zone.longitude = float(payload.longitude)
        zone.radius = float(payload.radius)
        zone.updated_at_ms = now_timestamp_ms()
        device.updated_at = utc_now()
        session.commit()

        print(
            f"[safe-zone] device={anonymize_device_id(device.device_id)} active radius={zone.radius}",
            flush=True,
        )
        return serialize_safe_zone(zone, device_id=device.device_id)

    @app.delete("/api/safe-zone")
    def clear_safe_zone(
        deviceId: str | None = None,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        device = resolve_device(session, deviceId)
        if not device:
            raise HTTPException(status_code=400, detail="deviceId is required")

        zone = session.scalar(select(SafeZone).where(SafeZone.device_fk == device.id))
        if not zone:
            zone = SafeZone(device_fk=device.id)
            session.add(zone)

        zone.active = False
        zone.latitude = None
        zone.longitude = None
        zone.radius = None
        zone.updated_at_ms = now_timestamp_ms()
        device.updated_at = utc_now()
        session.commit()

        print(f"[safe-zone] device={anonymize_device_id(device.device_id)} cleared", flush=True)
        return serialize_safe_zone(zone, device_id=device.device_id)

    @app.post("/api/push/register")
    def register_push_token(payload: PushRegisterIn, session: Session = Depends(get_session)) -> dict[str, Any]:
        token = payload.token.strip()
        if not token:
            raise HTTPException(status_code=400, detail="token is required")

        token_row = session.scalar(select(PushToken).where(PushToken.token == token))
        if not token_row:
            token_row = PushToken(token=token)
            session.add(token_row)

        token_row.platform = payload.platform
        token_row.active = True
        token_row.updated_at = utc_now()
        if payload.deviceId:
            token_row.device = get_or_create_device(session, payload.deviceId.strip())
        else:
            token_row.device = None
        session.commit()
        return {"status": "registered"}

    @app.delete("/api/push/register")
    def deactivate_push_token(token: str, session: Session = Depends(get_session)) -> dict[str, Any]:
        token_row = session.scalar(select(PushToken).where(PushToken.token == token))
        if token_row:
            token_row.active = False
            token_row.updated_at = utc_now()
            session.commit()
        return {"status": "removed"}

    @app.websocket("/api/ws/alerts")
    async def alert_ws(websocket: WebSocket) -> None:
        device_id = websocket.query_params.get("deviceId")
        await broadcaster.connect(websocket, device_id)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await broadcaster.disconnect(websocket)
        except Exception:
            await broadcaster.disconnect(websocket)

    return app


app = create_app()


def run() -> None:
    settings = load_settings()
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nServer stopped", flush=True)
        sys.exit(0)
