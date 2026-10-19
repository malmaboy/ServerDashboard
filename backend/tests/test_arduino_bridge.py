import asyncio
import os
import sys
import unittest
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import arduino_bridge  # noqa: E402

AGENT_ACTIVE = {
    "enabled": True,
    "state": "active",
    "socatRunning": True,
    "listening": True,
    "serialPresent": True,
    "serialDevices": ["/dev/ttyACM0"],
    "port": 5555,
    "baud": 9600,
    "desired": True,
    "managed": True,
    "pids": [123],
    "evil": "<script>",
}


def patched_agent(handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    return mock.patch("app.arduino_bridge.httpx.AsyncClient", factory)


class NormalizeTests(unittest.TestCase):
    def test_whitelists_fields(self):
        out = arduino_bridge.normalize_bridge_status(AGENT_ACTIVE)
        self.assertEqual(out["state"], "active")
        self.assertTrue(out["supported"])
        self.assertNotIn("evil", out)
        self.assertNotIn("pids", out)

    def test_disabled_or_garbage_is_unsupported(self):
        self.assertEqual(arduino_bridge.normalize_bridge_status({"enabled": False}), {"supported": False})
        self.assertEqual(arduino_bridge.normalize_bridge_status("x"), {"supported": False})

    def test_unknown_state_is_sanitised(self):
        out = arduino_bridge.normalize_bridge_status({**AGENT_ACTIVE, "state": "rm -rf /"})
        self.assertEqual(out["state"], "unknown")


class StatusTests(unittest.TestCase):
    def test_ok(self):
        with patched_agent(lambda req: httpx.Response(200, json=AGENT_ACTIVE)):
            out = asyncio.run(arduino_bridge.get_arduino_bridge_status())
        self.assertEqual(out["state"], "active")

    def test_old_agent_404_means_unsupported(self):
        with patched_agent(lambda req: httpx.Response(404, json={"detail": "Not Found"})):
            out = asyncio.run(arduino_bridge.get_arduino_bridge_status())
        self.assertEqual(out, {"supported": False})

    def test_unreachable_agent_returns_none(self):
        def boom(req):
            raise httpx.ConnectError("down")

        with patched_agent(boom):
            self.assertIsNone(asyncio.run(arduino_bridge.get_arduino_bridge_status()))


class ActionTests(unittest.TestCase):
    def client(self):
        app = FastAPI()
        app.include_router(arduino_bridge.router)
        return TestClient(app)

    def test_rejects_unknown_actions_before_calling_agent(self):
        calls = []
        with patched_agent(lambda req: calls.append(req) or httpx.Response(200, json=AGENT_ACTIVE)):
            r = self.client().post("/api/raspberry-pi/bridge/restart")
            r2 = self.client().post("/api/raspberry-pi/bridge/start;id")
        self.assertEqual(r.status_code, 400)
        self.assertIn(r2.status_code, (400, 404))
        self.assertEqual(calls, [])

    def test_start_proxies_to_agent_and_returns_status(self):
        seen = {}

        def handler(req):
            seen["url"] = str(req.url)
            seen["method"] = req.method
            return httpx.Response(200, json=AGENT_ACTIVE)

        with patched_agent(handler):
            r = self.client().post("/api/raspberry-pi/bridge/start")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["arduinoBridge"]["state"], "active")
        self.assertTrue(seen["url"].endswith("/bridge/start"))
        self.assertEqual(seen["method"], "POST")

    def test_token_header_sent_only_when_configured(self):
        seen = []
        with patched_agent(lambda req: seen.append(req.headers.get("x-agent-token")) or httpx.Response(200, json=AGENT_ACTIVE)):
            with mock.patch.object(arduino_bridge, "AGENT_TOKEN", "tok"):
                self.client().post("/api/raspberry-pi/bridge/stop")
            with mock.patch.object(arduino_bridge, "AGENT_TOKEN", ""):
                self.client().post("/api/raspberry-pi/bridge/stop")
        self.assertEqual(seen, ["tok", None])

    def test_agent_errors_are_mapped(self):
        cases = {409: 409, 404: 501, 401: 502, 500: 502}
        for agent_status, expected in cases.items():
            with self.subTest(agent_status=agent_status):
                with patched_agent(lambda req, s=agent_status: httpx.Response(s, json={"detail": "x"})):
                    r = self.client().post("/api/raspberry-pi/bridge/start")
                self.assertEqual(r.status_code, expected)

    def test_agent_down_gives_502(self):
        def boom(req):
            raise httpx.ConnectError("down")

        with patched_agent(boom):
            r = self.client().post("/api/raspberry-pi/bridge/start")
        self.assertEqual(r.status_code, 502)


if __name__ == "__main__":
    unittest.main()
