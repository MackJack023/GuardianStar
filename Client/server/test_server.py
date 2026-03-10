from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient


def load_server_module():
    server_path = Path(__file__).with_name("server.py")
    module_name = f"guardian_server_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, server_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GuardianBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_url = f"sqlite:///{(Path(cls.temp_dir.name) / 'test-backend.db').as_posix()}"
        cls.legacy_file = Path(cls.temp_dir.name) / "legacy.json"
        cls.module = load_server_module()
        cls.client_context = TestClient(
            cls.module.create_app(
                database_url=cls.db_url,
                legacy_state_file=cls.legacy_file,
                alert_webhook_url=None,
            )
        )
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.temp_dir.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        expect_status: int = 200,
    ) -> dict | list:
        response = self.client.request(method, path, json=payload)
        self.assertEqual(response.status_code, expect_status, response.text)
        body = response.json() if response.content else {}
        return body

    def test_health_endpoint(self) -> None:
        payload = self.request("GET", "/api/health")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["framework"], "fastapi")

    def test_multi_device_locations_are_isolated(self) -> None:
        self.request(
            "POST",
            "/api/location",
            {"deviceId": "device-A", "latitude": 1.1, "longitude": 2.2, "timestamp": 1700000000000},
        )
        self.request(
            "POST",
            "/api/location",
            {"deviceId": "device-B", "latitude": 3.3, "longitude": 4.4, "timestamp": 1700000001000},
        )

        devices = self.request("GET", "/api/devices")
        self.assertGreaterEqual(len(devices), 2)
        self.assertEqual(devices[0]["deviceId"], "device-B")

        latest_a = self.request("GET", "/api/latest?deviceId=device-A")
        latest_b = self.request("GET", "/api/latest?deviceId=device-B")
        self.assertEqual(latest_a["deviceId"], "device-A")
        self.assertEqual(latest_b["deviceId"], "device-B")

    def test_safe_zone_is_scoped_per_device(self) -> None:
        self.request(
            "POST",
            "/api/safe-zone",
            {"deviceId": "device-B", "latitude": 3.3, "longitude": 4.4, "radius": 120},
        )

        safe_zone_b = self.request("GET", "/api/safe-zone?deviceId=device-B")
        safe_zone_a = self.request("GET", "/api/safe-zone?deviceId=device-A")
        self.assertTrue(safe_zone_b["active"])
        self.assertEqual(safe_zone_b["deviceId"], "device-B")
        self.assertFalse(safe_zone_a["active"])

        cleared = self.request("DELETE", "/api/safe-zone?deviceId=device-B")
        self.assertFalse(cleared["active"])

    def test_location_payload_requires_coordinates(self) -> None:
        response = self.request(
            "POST",
            "/api/location",
            {"deviceId": "device-C", "timestamp": 1700000002000},
            expect_status=422,
        )
        self.assertIn("latitude", json.dumps(response))

    def test_safe_zone_radius_must_be_positive(self) -> None:
        response = self.request(
            "POST",
            "/api/safe-zone",
            {"deviceId": "device-D", "latitude": 1.2, "longitude": 2.3, "radius": 0},
            expect_status=422,
        )
        self.assertIn("radius", json.dumps(response))

    def test_websocket_alert_push(self) -> None:
        with self.client.websocket_connect("/api/ws/alerts?deviceId=device-ws") as websocket:
            self.request(
                "POST",
                "/api/alert",
                {"deviceId": "device-ws", "type": "EXIT", "timestamp": 1700000005000},
            )
            payload = websocket.receive_json()
            self.assertEqual(payload["deviceId"], "device-ws")
            self.assertEqual(payload["type"], "EXIT")

    def test_legacy_state_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_payload = {
                "location_history": [
                    {"deviceId": "legacy-device", "latitude": 30.0, "longitude": 120.0, "timestamp": 1700000010000}
                ],
                "alerts": [{"deviceId": "legacy-device", "type": "EXIT", "timestamp": 1700000015000}],
                "safe_zone": {"active": True, "latitude": 30.0, "longitude": 120.0, "radius": 100.0},
            }
            legacy_file = Path(temp_dir) / "legacy-state.json"
            legacy_file.write_text(json.dumps(legacy_payload), encoding="utf-8")
            db_url = f"sqlite:///{(Path(temp_dir) / 'legacy-test.db').as_posix()}"
            module = load_server_module()

            with TestClient(
                module.create_app(
                    database_url=db_url,
                    legacy_state_file=legacy_file,
                    alert_webhook_url=None,
                )
            ) as client:
                devices = client.get("/api/devices").json()
                self.assertEqual(len(devices), 1)
                self.assertEqual(devices[0]["deviceId"], "legacy-device")
                safe_zone = client.get("/api/safe-zone?deviceId=legacy-device").json()
                self.assertTrue(safe_zone["active"])


if __name__ == "__main__":
    unittest.main()
