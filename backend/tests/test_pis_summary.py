import asyncio
import json
import os
import sys
import time
import unittest
from unittest import mock

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import pis_summary, raspberry_pi  # noqa: E402

PI1_URL = raspberry_pi.RASPBERRY_PI_URL
PI2_URL = raspberry_pi.RASPBERRY_PI_2_URL

HEALTHY = {
    "cpu": 4.5,
    "ram_used_gb": 0.4,
    "ram_total_gb": 3.71,
    "uptime_seconds": 3485342,
    "containers": [
        {"name": "pihole", "status": "running", "image": "pihole/pihole:latest", "ports": ["0.0.0.0:53"]},
        {"name": "agent", "status": "exited", "image": "abc123", "ports": []},
    ],
}


def fake_fetch(responses: dict):
    """Build a stand-in for fetch_pi_stats_payload keyed by URL (value or exception)."""

    async def fetch(url: str, timeout: float = 3.0):
        result = responses[url]
        if isinstance(result, BaseException):
            raise result
        return result

    return fetch


def run_summary(responses: dict) -> dict:
    with mock.patch.object(raspberry_pi, "fetch_pi_stats_payload", fake_fetch(responses)):
        return asyncio.run(pis_summary.get_pis_summary())


class HealthyTests(unittest.TestCase):
    def test_both_healthy(self) -> None:
        result = run_summary({PI1_URL: HEALTHY, PI2_URL: HEALTHY})
        self.assertEqual([p["id"] for p in result["pis"]], ["pi1", "pi2"])
        self.assertEqual(result["pis"][0]["name"], "Raspberry Pi 1 — Pi-hole")
        self.assertEqual(result["pis"][1]["name"], "Raspberry Pi 2 — GardenAssistant (prod)")
        pi1 = result["pis"][0]
        self.assertTrue(pi1["reachable"])
        self.assertEqual(pi1["cpu"], 4.5)
        self.assertEqual(pi1["ram_used_gb"], 0.4)
        self.assertEqual(pi1["ram_total_gb"], 3.71)
        self.assertEqual(pi1["ram_pct"], 10.8)
        self.assertEqual(pi1["uptime_seconds"], 3485342)
        self.assertNotIn("error", pi1)
        json.dumps(result, allow_nan=False)

    def test_containers_trimmed_to_name_and_status(self) -> None:
        pi1 = run_summary({PI1_URL: HEALTHY, PI2_URL: HEALTHY})["pis"][0]
        self.assertEqual(
            pi1["containers"],
            [{"name": "pihole", "status": "running"}, {"name": "agent", "status": "exited"}],
        )

    def test_malformed_container_entries_are_skipped(self) -> None:
        payload = dict(HEALTHY, containers=["x", None, {"status": "running"}, {"name": 5}, {"name": "ok"}])
        pi1 = run_summary({PI1_URL: payload, PI2_URL: HEALTHY})["pis"][0]
        self.assertEqual(pi1["containers"], [{"name": "ok", "status": None}])

    def test_containers_not_a_list_gives_empty_list(self) -> None:
        pi1 = run_summary({PI1_URL: dict(HEALTHY, containers="nope"), PI2_URL: HEALTHY})["pis"][0]
        self.assertEqual(pi1["containers"], [])


class FailureTests(unittest.TestCase):
    def test_one_pi_down_does_not_affect_the_other(self) -> None:
        result = run_summary({PI1_URL: HEALTHY, PI2_URL: httpx.ConnectTimeout("http://secret-host:9090")})
        pi1, pi2 = result["pis"]
        self.assertTrue(pi1["reachable"])
        self.assertEqual(pi2, {
            "id": "pi2",
            "name": "Raspberry Pi 2 — GardenAssistant (prod)",
            "reachable": False,
            "error": "timeout",
        })

    def test_both_down(self) -> None:
        result = run_summary({PI1_URL: httpx.ConnectError("refused 192.168.0.130"), PI2_URL: OSError("boom")})
        self.assertEqual([p["reachable"] for p in result["pis"]], [False, False])
        self.assertEqual(result["pis"][0]["error"], "connection failed")
        self.assertEqual(result["pis"][1]["error"], "unavailable")
        for pi in result["pis"]:
            self.assertEqual(set(pi), {"id", "name", "reachable", "error"})

    def test_errors_do_not_leak_urls_or_hosts(self) -> None:
        errors = [
            httpx.ConnectError(f"cannot reach {PI1_URL}"),
            httpx.ConnectTimeout(PI1_URL),
            RuntimeError(PI1_URL),
            ValueError(PI1_URL),
        ]
        for exc in errors:
            with self.subTest(exc=type(exc).__name__):
                pi = run_summary({PI1_URL: exc, PI2_URL: HEALTHY})["pis"][0]
                self.assertNotIn("192.168", json.dumps(pi))
                self.assertNotIn("http", pi["error"])

    def test_http_error_status(self) -> None:
        request = httpx.Request("GET", f"{PI1_URL}/stats")
        exc = httpx.HTTPStatusError("bad", request=request, response=httpx.Response(503, request=request))
        pi = run_summary({PI1_URL: exc, PI2_URL: HEALTHY})["pis"][0]
        self.assertEqual(pi["error"], "http 503")

    def test_bad_json_and_non_dict_payloads(self) -> None:
        bad = [json.JSONDecodeError("x", "", 0), [], "text", 42, None]
        for payload in bad:
            with self.subTest(payload=repr(payload)):
                pi1, pi2 = run_summary({PI1_URL: payload, PI2_URL: HEALTHY})["pis"]
                self.assertEqual(pi1["reachable"], False)
                self.assertEqual(pi1["error"], "invalid response")
                self.assertTrue(pi2["reachable"])

    def test_empty_dict_is_reachable_with_null_metrics(self) -> None:
        pi1 = run_summary({PI1_URL: {}, PI2_URL: HEALTHY})["pis"][0]
        self.assertTrue(pi1["reachable"])
        for key in ("cpu", "ram_used_gb", "ram_total_gb", "ram_pct", "uptime_seconds"):
            self.assertIsNone(pi1[key])
        self.assertEqual(pi1["containers"], [])

    def test_slow_pi_times_out_without_delaying_the_other(self) -> None:
        async def fetch(url: str, timeout: float = 3.0):
            if url == PI1_URL:
                await asyncio.sleep(30)
            return HEALTHY

        with mock.patch.object(raspberry_pi, "fetch_pi_stats_payload", fetch), mock.patch.object(
            pis_summary, "PI_TIMEOUT_SECONDS", 0.05
        ):
            started = time.monotonic()
            result = asyncio.run(pis_summary.get_pis_summary())
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2)
        self.assertEqual(result["pis"][0]["error"], "timeout")
        self.assertTrue(result["pis"][1]["reachable"])

    def test_unexpected_exception_returns_unreachable_shape(self) -> None:
        with mock.patch.object(pis_summary, "_summarize_pi", side_effect=RuntimeError("boom")):
            result = asyncio.run(pis_summary.get_pis_summary())
        self.assertEqual([p["id"] for p in result["pis"]], ["pi1", "pi2"])
        for pi in result["pis"]:
            self.assertEqual(set(pi), {"id", "name", "reachable", "error"})
            self.assertFalse(pi["reachable"])


class RamTests(unittest.TestCase):
    def pi1(self, **overrides) -> dict:
        payload = dict(HEALTHY, **overrides)
        return run_summary({PI1_URL: payload, PI2_URL: HEALTHY})["pis"][0]

    def test_ram_pct_math(self) -> None:
        pi = self.pi1(ram_used_gb=1.0, ram_total_gb=4.0)
        self.assertEqual(pi["ram_pct"], 25.0)
        pi = self.pi1(ram_used_gb=0, ram_total_gb=4.0)
        self.assertEqual(pi["ram_pct"], 0.0)
        pi = self.pi1(ram_used_gb=1.0, ram_total_gb=3.0)
        self.assertEqual(pi["ram_pct"], 33.3)

    def test_zero_total_gives_null_pct(self) -> None:
        pi = self.pi1(ram_used_gb=1.0, ram_total_gb=0)
        self.assertIsNone(pi["ram_pct"])

    def test_nan_inf_negative_ram_rejected(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf"), -1.0, -0.5):
            for key in ("ram_used_gb", "ram_total_gb"):
                with self.subTest(bad=bad, key=key):
                    pi = self.pi1(**{key: bad})
                    self.assertIsNone(pi[key])
                    self.assertIsNone(pi["ram_pct"])
                    self.assertTrue(pi["reachable"])

    def test_non_numeric_values_rejected(self) -> None:
        for bad in ("3.7", None, True, [], {}):
            with self.subTest(bad=bad):
                pi = self.pi1(ram_total_gb=bad, cpu=bad, uptime_seconds=bad)
                self.assertIsNone(pi["ram_total_gb"])
                self.assertIsNone(pi["ram_pct"])
                self.assertIsNone(pi["cpu"])
                self.assertIsNone(pi["uptime_seconds"])

    def test_bad_values_stay_json_serialisable(self) -> None:
        pi = self.pi1(cpu=float("nan"), ram_used_gb=float("inf"), uptime_seconds=float("-inf"))
        json.dumps(pi, allow_nan=False)

    def test_overflowing_ratio_gives_null_pct(self) -> None:
        pi = self.pi1(ram_used_gb=1e308, ram_total_gb=1e-300)
        self.assertIsNone(pi["ram_pct"])


class FetchLayerTests(unittest.TestCase):
    """fetch_pi_stats_payload against a mocked HTTP transport (no real network)."""

    def fetch(self, handler, url: str = PI1_URL):
        real_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

        with mock.patch.object(raspberry_pi.httpx, "AsyncClient", client_factory):
            return asyncio.run(raspberry_pi.fetch_pi_stats_payload(url, timeout=1.0))

    def test_only_get_stats_is_requested(self) -> None:
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.method, str(request.url)))
            return httpx.Response(200, json=HEALTHY)

        self.assertEqual(self.fetch(handler), HEALTHY)
        self.assertEqual(seen, [("GET", f"{PI1_URL}/stats")])

    def test_http_error_raises(self) -> None:
        with self.assertRaises(httpx.HTTPStatusError):
            self.fetch(lambda request: httpx.Response(500))

    def test_end_to_end_with_mocked_transport(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).startswith(PI2_URL):
                raise httpx.ConnectError("refused", request=request)
            return httpx.Response(200, json=HEALTHY)

        real_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

        with mock.patch.object(raspberry_pi.httpx, "AsyncClient", client_factory):
            result = asyncio.run(pis_summary.get_pis_summary())
        self.assertTrue(result["pis"][0]["reachable"])
        self.assertEqual(result["pis"][1]["error"], "connection failed")

    def test_bad_json_body_is_invalid_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>not json</html>")

        real_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

        with mock.patch.object(raspberry_pi.httpx, "AsyncClient", client_factory):
            result = asyncio.run(pis_summary.get_pis_summary())
        for pi in result["pis"]:
            self.assertEqual(pi["error"], "invalid response")


class RouteTests(unittest.TestCase):
    def test_route_returns_200_with_pis(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        responses = {PI1_URL: HEALTHY, PI2_URL: httpx.ConnectTimeout("t")}
        with mock.patch.object(raspberry_pi, "fetch_pi_stats_payload", fake_fetch(responses)):
            response = TestClient(app).get("/api/pis/summary")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(list(body), ["pis"])
        self.assertTrue(body["pis"][0]["reachable"])
        self.assertEqual(body["pis"][1]["error"], "timeout")

    def test_route_is_200_even_on_unexpected_error(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        with mock.patch.object(pis_summary, "_summarize_pi", side_effect=RuntimeError("boom")):
            response = TestClient(app).get("/api/pis/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["reachable"] for p in response.json()["pis"]], [False, False])


if __name__ == "__main__":
    unittest.main()
