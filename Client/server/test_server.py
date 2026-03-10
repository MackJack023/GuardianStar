from __future__ import annotations

import importlib.util
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


class GuardianServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["GUARDIANSTAR_STATE_FILE"] = str(Path(cls.temp_dir.name) / "server_state.json")

        server_path = Path(__file__).with_name("server.py")
        spec = importlib.util.spec_from_file_location("guardian_server", server_path)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 8093), cls.module.LocationHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.thread.join(timeout=2)
        cls.httpd.server_close()
        cls.temp_dir.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        expect_status: int = 200,
    ) -> dict | list:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:8093{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            status_code = error.code
            body = error.read().decode("utf-8")
            error.close()

        self.assertEqual(status_code, expect_status)
        return json.loads(body)

    def test_health_endpoint(self) -> None:
        payload = self.request("GET", "/api/health")
        self.assertEqual(payload["status"], "ok")

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
        self.assertEqual(len(devices), 2)
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
            expect_status=400,
        )
        self.assertIn("latitude and longitude", response["error"])

    def test_safe_zone_radius_must_be_positive(self) -> None:
        response = self.request(
            "POST",
            "/api/safe-zone",
            {"deviceId": "device-D", "latitude": 1.2, "longitude": 2.3, "radius": 0},
            expect_status=400,
        )
        self.assertIn("radius must be greater than 0", response["error"])


if __name__ == "__main__":
    unittest.main()
