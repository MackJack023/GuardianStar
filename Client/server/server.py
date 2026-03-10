from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import datetime as dt
import json
import os
import sys
from typing import Any


PORT = int(os.getenv("PORT", "8080"))
MAX_HISTORY = 200
MAX_ALERTS = 200
STATE_FILE = Path(os.getenv("GUARDIANSTAR_STATE_FILE", str(Path(__file__).with_name("server_state.json"))))


def now_timestamp_ms() -> int:
    return int(dt.datetime.now().timestamp() * 1000)


def format_timestamp(timestamp_ms: int) -> str:
    return dt.datetime.fromtimestamp(timestamp_ms / 1000.0).strftime("%Y-%m-%d %H:%M:%S")


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


def migrate_state(raw: dict[str, Any]) -> dict[str, Any]:
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

    normalized = {
        "devices": {
            device_id: normalize_device_state(device_id, device_state)
            for device_id, device_state in devices.items()
        }
    }
    return normalized


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"devices": {}}

    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"devices": {}}

    return migrate_state(raw)


STATE = load_state()


def save_state() -> None:
    STATE_FILE.write_text(
        json.dumps(STATE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def parse_request(handler: BaseHTTPRequestHandler) -> tuple[str, dict[str, str]]:
    parsed = urlparse(handler.path)
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    return parsed.path, query


def get_device_state(device_id: str, create: bool = False) -> dict[str, Any] | None:
    devices = STATE.setdefault("devices", {})
    if create and device_id not in devices:
        devices[device_id] = empty_device_state(device_id)
    return devices.get(device_id)


def sorted_devices() -> list[dict[str, Any]]:
    devices = list(STATE.get("devices", {}).values())

    def sort_key(device_state: dict[str, Any]) -> int:
        return int(device_state.get("last_location", {}).get("timestamp", 0))

    return sorted(devices, key=sort_key, reverse=True)


def latest_device_state() -> dict[str, Any] | None:
    devices = sorted_devices()
    return devices[0] if devices else None


def resolve_device_state(device_id: str | None) -> dict[str, Any] | None:
    if device_id:
        return get_device_state(device_id, create=False)
    return latest_device_state()


def html_page() -> str:
    active_device = latest_device_state()
    device_count = len(STATE.get("devices", {}))

    if not active_device or not active_device.get("last_location"):
        status_html = "<p>Waiting for a child device to upload location data...</p>"
        location_summary = "No device connected yet"
    else:
        last_location = active_device["last_location"]
        safe_zone = active_device["safe_zone"]
        latitude = last_location.get("latitude")
        longitude = last_location.get("longitude")
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            location_summary = f"{float(latitude):.5f}, {float(longitude):.5f}"
        else:
            location_summary = "Unknown"
        status_html = f"""
            <div class="info-item"><span class="label">Device:</span><span class="value">{active_device['deviceId'][-6:].upper()}</span></div>
            <div class="info-item"><span class="label">Updated:</span><span class="value">{last_location.get('time_str')}</span></div>
            <div class="info-item"><span class="label">Location:</span><span class="value">{location_summary}</span></div>
            <div class="info-item"><span class="label">Safe Zone:</span><span class="value">{'Active' if safe_zone.get('active') else 'Not configured'}</span></div>
            <div class="info-item"><span class="label">Devices:</span><span class="value">{device_count}</span></div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="10">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GuardianStar Monitor</title>
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


def device_summary(device_state: dict[str, Any]) -> dict[str, Any]:
    last_location = device_state.get("last_location", {})
    timestamp = last_location.get("timestamp")
    return {
        "deviceId": device_state["deviceId"],
        "lastUpdatedAt": timestamp,
        "lastUpdatedText": last_location.get("time_str"),
        "latitude": last_location.get("latitude"),
        "longitude": last_location.get("longitude"),
        "safeZoneActive": bool(device_state.get("safe_zone", {}).get("active", False)),
    }


class LocationHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path, query = parse_request(self)

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_page().encode("utf-8"))
            return

        if path == "/api/health":
            json_response(self, 200, {"status": "ok", "time": format_timestamp(now_timestamp_ms())})
            return

        if path == "/api/devices":
            json_response(self, 200, [device_summary(device) for device in sorted_devices()])
            return

        if path == "/api/latest":
            device = resolve_device_state(query.get("deviceId"))
            json_response(self, 200, device.get("last_location", {}) if device else {})
            return

        if path == "/api/history":
            device = resolve_device_state(query.get("deviceId"))
            json_response(self, 200, device.get("location_history", []) if device else [])
            return

        if path == "/api/alerts":
            device = resolve_device_state(query.get("deviceId"))
            json_response(self, 200, device.get("alerts", []) if device else [])
            return

        if path == "/api/safe-zone":
            device = resolve_device_state(query.get("deviceId"))
            if not device:
                json_response(self, 200, {"active": False})
                return
            json_response(self, 200, device.get("safe_zone", {"active": False}))
            return

        json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:
        path, _query = parse_request(self)
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            json_response(self, 400, {"error": "Invalid JSON"})
            return

        if path == "/api/location":
            device_id = str(payload.get("deviceId") or "").strip()
            if not device_id:
                json_response(self, 400, {"error": "deviceId is required"})
                return

            try:
                latitude = float(payload["latitude"])
                longitude = float(payload["longitude"])
            except (KeyError, TypeError, ValueError):
                json_response(self, 400, {"error": "latitude and longitude are required"})
                return

            try:
                timestamp = int(payload.get("timestamp", now_timestamp_ms()))
            except (TypeError, ValueError):
                timestamp = now_timestamp_ms()

            location_payload = dict(payload)
            location_payload["deviceId"] = device_id
            location_payload["latitude"] = latitude
            location_payload["longitude"] = longitude
            location_payload["timestamp"] = timestamp
            location_payload["time_str"] = format_timestamp(timestamp)

            device = get_device_state(device_id, create=True)
            device["last_location"] = location_payload
            device["location_history"].append(location_payload)
            device["location_history"] = device["location_history"][-MAX_HISTORY:]
            save_state()

            print(
                f"[location] device={device_id} time={location_payload['time_str']} "
                f"lat={location_payload.get('latitude')} lng={location_payload.get('longitude')}"
            )
            json_response(self, 200, {"status": "success"})
            return

        if path == "/api/alert":
            device_id = str(payload.get("deviceId") or "").strip()
            if not device_id:
                json_response(self, 400, {"error": "deviceId is required"})
                return

            timestamp = int(payload.get("timestamp", now_timestamp_ms()))
            payload["time_str"] = format_timestamp(timestamp)

            device = get_device_state(device_id, create=True)
            device["alerts"].insert(0, payload)
            device["alerts"] = device["alerts"][:MAX_ALERTS]
            save_state()

            print(f"[alert] device={device_id} time={payload['time_str']} type={payload.get('type')}")
            json_response(self, 200, {"status": "success"})
            return

        if path == "/api/safe-zone":
            device_id = str(payload.get("deviceId") or "").strip()
            if not device_id:
                json_response(self, 400, {"error": "deviceId is required"})
                return

            try:
                latitude = float(payload["latitude"])
                longitude = float(payload["longitude"])
                radius = float(payload.get("radius", 100.0))
            except (KeyError, TypeError, ValueError):
                json_response(self, 400, {"error": "latitude, longitude and radius are required"})
                return
            if radius <= 0:
                json_response(self, 400, {"error": "radius must be greater than 0"})
                return

            device = get_device_state(device_id, create=True)
            device["safe_zone"] = {
                "active": True,
                "deviceId": device_id,
                "latitude": latitude,
                "longitude": longitude,
                "radius": radius,
                "updatedAt": now_timestamp_ms(),
            }
            save_state()

            print(f"[safe-zone] device={device_id} active lat={latitude} lng={longitude} radius={radius}")
            json_response(self, 200, device["safe_zone"])
            return

        json_response(self, 404, {"error": "Not found"})

    def do_DELETE(self) -> None:
        path, query = parse_request(self)

        if path == "/api/safe-zone":
            device_id = str(query.get("deviceId") or "").strip()
            if not device_id:
                latest = latest_device_state()
                if latest:
                    device_id = latest["deviceId"]

            if not device_id:
                json_response(self, 400, {"error": "deviceId is required"})
                return

            device = get_device_state(device_id, create=True)
            device["safe_zone"] = {
                "active": False,
                "deviceId": device_id,
                "updatedAt": now_timestamp_ms(),
            }
            save_state()
            print(f"[safe-zone] device={device_id} cleared")
            json_response(self, 200, device["safe_zone"])
            return

        json_response(self, 404, {"error": "Not found"})

    def log_message(self, _format: str, *_args: Any) -> None:
        return


if __name__ == "__main__":
    server_address = ("", PORT)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, LocationHandler)

    print("GuardianStar backend started")
    print(f"Health: http://localhost:{PORT}/api/health")
    print(f"Devices: http://localhost:{PORT}/api/devices")
    print(f"Latest location: http://localhost:{PORT}/api/latest")
    print(f"Monitor page: http://localhost:{PORT}/")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
