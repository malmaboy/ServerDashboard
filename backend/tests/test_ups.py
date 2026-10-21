import asyncio
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import ups  # noqa: E402


class ComputePowerTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("UPS_NOMINAL_WATTS", None)

    def test_estimated_uses_default_nominal(self) -> None:
        result = ups.compute_power({"ups.load": "9"})
        self.assertEqual(result, {"power": 65, "powerSource": "estimated", "nominalPower": 720})

    def test_estimated_uses_reported_nominal(self) -> None:
        result = ups.compute_power({"ups.load": "50", "ups.realpower.nominal": "600"})
        self.assertEqual(result, {"power": 300, "powerSource": "estimated", "nominalPower": 600})

    def test_reported_nominal_wins_over_env(self) -> None:
        os.environ["UPS_NOMINAL_WATTS"] = "1000"
        result = ups.compute_power({"ups.load": "10", "ups.realpower.nominal": "500"})
        self.assertEqual(result["power"], 50)
        self.assertEqual(result["nominalPower"], 500)

    def test_env_override(self) -> None:
        os.environ["UPS_NOMINAL_WATTS"] = "480"
        result = ups.compute_power({"ups.load": "25"})
        self.assertEqual(result, {"power": 120, "powerSource": "estimated", "nominalPower": 480})

    def test_invalid_env_falls_back_to_default(self) -> None:
        for bad in ("abc", "0", "-5", ""):
            with self.subTest(bad=bad):
                os.environ["UPS_NOMINAL_WATTS"] = bad
                self.assertEqual(ups.compute_power({"ups.load": "10"})["nominalPower"], 720)

    def test_measured_preferred_over_load(self) -> None:
        result = ups.compute_power({"ups.realpower": "87.4", "ups.load": "90"})
        self.assertEqual(result, {"power": 87, "powerSource": "measured", "nominalPower": 720})

    def test_missing_load_gives_null_power(self) -> None:
        result = ups.compute_power({})
        self.assertEqual(result, {"power": None, "powerSource": None, "nominalPower": 720})

    def test_non_numeric_load_gives_null_power(self) -> None:
        result = ups.compute_power({"ups.load": "n/a"})
        self.assertIsNone(result["power"])
        self.assertIsNone(result["powerSource"])

    def test_non_finite_values_are_ignored(self) -> None:
        for bad in ("nan", "inf", "-inf", "NaN", "Infinity"):
            with self.subTest(bad=bad):
                self.assertEqual(
                    ups.compute_power({"ups.load": bad}),
                    {"power": None, "powerSource": None, "nominalPower": 720},
                )
                self.assertEqual(
                    ups.compute_power({"ups.realpower": bad}),
                    {"power": None, "powerSource": None, "nominalPower": 720},
                )
                # bad measured value falls back to the load estimate
                self.assertEqual(
                    ups.compute_power({"ups.realpower": bad, "ups.load": "10"}),
                    {"power": 72, "powerSource": "estimated", "nominalPower": 720},
                )
                # bad reported nominal falls back to the default
                result = ups.compute_power({"ups.load": "10", "ups.realpower.nominal": bad})
                self.assertEqual(result["nominalPower"], 720)
                self.assertEqual(result["power"], 72)

    def test_non_finite_env_falls_back_to_default(self) -> None:
        for bad in ("inf", "-inf", "nan"):
            with self.subTest(bad=bad):
                os.environ["UPS_NOMINAL_WATTS"] = bad
                result = ups.compute_power({"ups.load": "10"})
                self.assertEqual(result["nominalPower"], 720)
                self.assertEqual(result["power"], 72)

    def test_overflowing_estimate_gives_null_power(self) -> None:
        result = ups.compute_power({"ups.load": "1e308", "ups.realpower.nominal": "1e308"})
        self.assertIsNone(result["power"])
        self.assertIsNone(result["powerSource"])

    def test_negative_load_gives_null_power(self) -> None:
        result = ups.compute_power({"ups.load": "-5"})
        self.assertEqual(result, {"power": None, "powerSource": None, "nominalPower": 720})

    def test_negative_realpower_is_invalid(self) -> None:
        self.assertEqual(
            ups.compute_power({"ups.realpower": "-3"}),
            {"power": None, "powerSource": None, "nominalPower": 720},
        )
        self.assertEqual(
            ups.compute_power({"ups.realpower": "-3", "ups.load": "10"}),
            {"power": 72, "powerSource": "estimated", "nominalPower": 720},
        )

    def test_zero_values_are_valid(self) -> None:
        self.assertEqual(
            ups.compute_power({"ups.realpower": "0"}),
            {"power": 0, "powerSource": "measured", "nominalPower": 720},
        )
        self.assertEqual(ups.compute_power({"ups.load": "0"})["power"], 0)

    def test_reported_nominal_not_positive_falls_back(self) -> None:
        for bad in ("0", "-100"):
            with self.subTest(bad=bad):
                result = ups.compute_power({"ups.load": "50", "ups.realpower.nominal": bad})
                self.assertEqual(result, {"power": 360, "powerSource": "estimated", "nominalPower": 720})
        os.environ["UPS_NOMINAL_WATTS"] = "480"
        result = ups.compute_power({"ups.load": "50", "ups.realpower.nominal": "0"})
        self.assertEqual(result, {"power": 240, "powerSource": "estimated", "nominalPower": 480})

    def test_measured_with_reported_nominal(self) -> None:
        result = ups.compute_power(
            {"ups.realpower": "123.6", "ups.load": "90", "ups.realpower.nominal": "600"}
        )
        self.assertEqual(result, {"power": 124, "powerSource": "measured", "nominalPower": 600})


class BuildSummaryTests(unittest.TestCase):
    def test_runtime_reported(self) -> None:
        summary = ups.build_summary({"battery.runtime": "1234.6", "ups.load": "9"})
        self.assertEqual(summary["runtimeSeconds"], 1235)

    def test_runtime_missing_is_null(self) -> None:
        self.assertIsNone(ups.build_summary({"ups.load": "9"})["runtimeSeconds"])

    def test_existing_fields_preserved(self) -> None:
        summary = ups.build_summary(
            {
                "ups.status": "OB LB",
                "battery.charge": "80",
                "battery.voltage": "25.1",
                "input.voltage": "0",
                "output.voltage": "230",
                "ups.load": "10",
                "ups.temperature": "30",
                "ups.beeper.status": "enabled",
                "ups.firmware": "V3.8",
            }
        )
        for key in (
            "name", "status", "onBattery", "lowBattery", "batteryCharge", "batteryVoltage",
            "inputVoltage", "outputVoltage", "load", "temperature", "beeperStatus", "firmware",
        ):
            self.assertIn(key, summary)
        self.assertTrue(summary["onBattery"])
        self.assertTrue(summary["lowBattery"])
        self.assertEqual(summary["batteryCharge"], 80.0)
        self.assertEqual(summary["load"], 10.0)

    def test_runtime_invalid_is_null(self) -> None:
        for bad in ("nan", "inf", "-inf", "-1", "n/a"):
            with self.subTest(bad=bad):
                self.assertIsNone(ups.build_summary({"battery.runtime": bad})["runtimeSeconds"])

    def test_summary_with_bad_values_is_json_serialisable(self) -> None:
        for bad in ("nan", "inf", "-inf", "-5"):
            with self.subTest(bad=bad):
                summary = ups.build_summary(
                    {
                        "ups.load": bad,
                        "ups.realpower": bad,
                        "ups.realpower.nominal": bad,
                        "battery.runtime": bad,
                        "battery.charge": bad,
                    }
                )
                json.dumps(summary, allow_nan=False)

    def test_summary_json_serialisable(self) -> None:
        summary = ups.build_summary({"ups.status": "OL", "ups.load": "9", "battery.runtime": "900"})
        decoded = json.loads(json.dumps(summary, allow_nan=False))
        self.assertEqual(decoded["power"], 65)
        self.assertEqual(decoded["powerSource"], "estimated")
        self.assertEqual(decoded["runtimeSeconds"], 900)


class GetUpsSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("UPS_NOMINAL_WATTS", None)

    def test_returns_none_when_nut_query_raises(self) -> None:
        with mock.patch.object(ups, "_query_nut_vars", side_effect=OSError("down")):
            self.assertIsNone(asyncio.run(ups.get_ups_summary()))

    def test_returns_none_when_summary_building_raises(self) -> None:
        async def fake(_name: str) -> dict[str, str]:
            return {"ups.load": "9"}

        with mock.patch.object(ups, "_query_nut_vars", fake), mock.patch.object(
            ups, "build_summary", side_effect=ValueError("boom")
        ):
            self.assertIsNone(asyncio.run(ups.get_ups_summary()))

    def test_returns_summary_with_bad_measured_value(self) -> None:
        async def fake(_name: str) -> dict[str, str]:
            return {"ups.load": "9", "ups.realpower": "nan"}

        with mock.patch.object(ups, "_query_nut_vars", fake):
            summary = asyncio.run(ups.get_ups_summary())
        self.assertIsNotNone(summary)
        self.assertEqual(summary["powerSource"], "estimated")
        self.assertEqual(summary["power"], 65)


if __name__ == "__main__":
    unittest.main()
