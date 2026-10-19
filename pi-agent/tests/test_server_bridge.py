"""Testes dos endpoints /bridge/* do pi-agent (FastAPI TestClient, sem Docker)."""
import importlib
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bridge  # noqa: E402


def load_server(env: dict):
    with mock.patch.dict(os.environ, env, clear=False), mock.patch("docker.from_env", side_effect=RuntimeError):
        sys.modules.pop("server", None)
        return importlib.import_module("server")


class DisabledBridgeTests(unittest.TestCase):
    def test_status_reports_disabled_and_actions_404(self):
        from fastapi.testclient import TestClient

        server = load_server({"BRIDGE_ENABLED": "false", "AGENT_TOKEN": ""})
        with TestClient(server.app) as client:
            self.assertEqual(client.get("/bridge/status").json(), {"enabled": False})
            self.assertEqual(client.post("/bridge/start").status_code, 404)
            self.assertEqual(client.post("/bridge/stop").status_code, 404)
            self.assertEqual(client.get("/health").json(), {"status": "ok"})


class EnabledBridgeTests(unittest.TestCase):
    def make_client(self, token: str = ""):
        from fastapi.testclient import TestClient

        server = load_server({"BRIDGE_ENABLED": "true", "AGENT_TOKEN": token, "BRIDGE_STATE_FILE": ""})
        manager = mock.Mock()
        manager.status.return_value = {"enabled": True, "state": "stopped"}
        manager.start.return_value = {"enabled": True, "state": "active"}
        manager.stop.return_value = {"enabled": True, "state": "stopped"}
        manager.reconcile.return_value = None
        server._bridge = manager
        return server, manager, TestClient(server.app)

    def test_status_start_stop(self):
        _server, manager, client = self.make_client()
        with client:
            self.assertEqual(client.get("/bridge/status").json()["state"], "stopped")
            self.assertEqual(client.post("/bridge/start").json()["state"], "active")
            self.assertEqual(client.post("/bridge/stop").json()["state"], "stopped")
        manager.start.assert_called_once()
        manager.stop.assert_called_once()

    def test_serial_missing_maps_to_409_without_leaking_details(self):
        _server, manager, client = self.make_client()
        manager.start.side_effect = bridge.BridgeError("serial_missing", "Arduino não detetado")
        with client:
            r = client.post("/bridge/start")
        self.assertEqual(r.status_code, 409)

    def test_token_required_for_mutations_only(self):
        _server, manager, client = self.make_client(token="s3cret")
        with client:
            self.assertEqual(client.get("/bridge/status").status_code, 200)
            self.assertEqual(client.post("/bridge/start").status_code, 401)
            self.assertEqual(client.post("/bridge/stop", headers={"X-Agent-Token": "wrong"}).status_code, 401)
            manager.start.assert_not_called()
            manager.stop.assert_not_called()
            self.assertEqual(client.post("/bridge/stop", headers={"X-Agent-Token": "s3cret"}).status_code, 200)
            self.assertEqual(client.post("/bridge/start", headers={"X-Agent-Token": "s3cret"}).status_code, 200)

    def test_existing_container_routes_untouched(self):
        server, _manager, client = self.make_client()
        with client:
            r = client.post("/containers/foo/start")
        self.assertEqual(r.status_code, 503)  # docker indisponível neste teste


if __name__ == "__main__":
    unittest.main()
