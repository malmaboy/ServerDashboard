import asyncio
import logging
import math
import os

logger = logging.getLogger(__name__)

NUT_HOST = os.getenv("NUT_HOST", "192.168.0.200")
NUT_PORT = int(os.getenv("NUT_PORT", "3493"))
NUT_USER = os.getenv("NUT_USER", "dashboard")
NUT_PASSWORD = os.getenv("NUT_PASSWORD", "")
NUT_UPS_NAME = os.getenv("NUT_UPS_NAME", "gembird")
# Gembird 1200VA class: ~0.6 power factor -> ~720 W. Only used to estimate
# power from ups.load when NUT does not report ups.realpower(.nominal).
DEFAULT_NOMINAL_WATTS = 720.0


async def _query_nut_vars(ups_name: str) -> dict[str, str]:
    reader, writer = await asyncio.open_connection(NUT_HOST, NUT_PORT)
    try:
        async def send(line: str) -> str:
            writer.write(f"{line}\n".encode())
            await writer.drain()
            return (await reader.readline()).decode().strip()

        if await send(f"USERNAME {NUT_USER}") != "OK":
            raise RuntimeError("NUT username rejected")
        if await send(f"PASSWORD {NUT_PASSWORD}") != "OK":
            raise RuntimeError("NUT password rejected")

        writer.write(f"LIST VAR {ups_name}\n".encode())
        await writer.drain()

        begin = (await reader.readline()).decode().strip()
        if not begin.startswith("BEGIN LIST VAR"):
            raise RuntimeError(f"unexpected NUT response: {begin}")

        values: dict[str, str] = {}
        end_marker = f"END LIST VAR {ups_name}"
        while True:
            line = (await reader.readline()).decode().strip()
            if line == end_marker:
                break
            # format: VAR <ups> <name> "<value>"
            parts = line.split(" ", 3)
            if len(parts) == 4 and parts[0] == "VAR":
                values[parts[2]] = parts[3].strip('"')
        return values
    finally:
        writer.write(b"LOGOUT\n")
        try:
            await writer.drain()
        except Exception:
            pass
        writer.close()


def _float(values: dict[str, str], key: str) -> float | None:
    raw = values.get(key)
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    # float() accepts "nan"/"inf"; those are never valid readings.
    return value if math.isfinite(value) else None


def _non_negative(values: dict[str, str], key: str) -> float | None:
    """Like _float, but a negative reading is invalid and treated as missing."""
    value = _float(values, key)
    return value if value is not None and value >= 0 else None


def _round_int(value: float) -> int | None:
    """round() that yields None instead of raising on non-finite values."""
    return round(value) if math.isfinite(value) else None


def _default_nominal_watts() -> float:
    """Fallback nominal real power, from UPS_NOMINAL_WATTS (invalid/<=0 -> default)."""
    try:
        watts = float(os.getenv("UPS_NOMINAL_WATTS", str(DEFAULT_NOMINAL_WATTS)))
    except ValueError:
        return DEFAULT_NOMINAL_WATTS
    return watts if math.isfinite(watts) and watts > 0 else DEFAULT_NOMINAL_WATTS


def compute_power(values: dict[str, str]) -> dict[str, int | str | None]:
    """Derive power draw (W), its source and the nominal power used.

    Prefers a measured ``ups.realpower``. Otherwise estimates it from
    ``ups.load`` (percent) times the nominal power, taken from
    ``ups.realpower.nominal`` when reported or from UPS_NOMINAL_WATTS.

    Invalid readings (non-numeric, nan/inf, negative) are treated as missing:
    a bad ``ups.realpower`` falls back to the load estimate, and a reported
    nominal <= 0 falls back to the env/default nominal.
    """
    measured = _non_negative(values, "ups.realpower")
    reported_nominal = _float(values, "ups.realpower.nominal")
    nominal = (
        reported_nominal
        if reported_nominal is not None and reported_nominal > 0
        else _default_nominal_watts()
    )
    nominal_power = _round_int(nominal)

    if measured is not None:
        power = _round_int(measured)
        if power is not None:
            return {"power": power, "powerSource": "measured", "nominalPower": nominal_power}

    load = _non_negative(values, "ups.load")
    power = _round_int(load / 100 * nominal) if load is not None else None
    if power is None:
        return {"power": None, "powerSource": None, "nominalPower": nominal_power}
    return {"power": power, "powerSource": "estimated", "nominalPower": nominal_power}


def _runtime_seconds(values: dict[str, str]) -> int | None:
    runtime = _non_negative(values, "battery.runtime")
    return _round_int(runtime) if runtime is not None else None


def build_summary(values: dict[str, str]) -> dict:
    status = values.get("ups.status", "")
    return {
        "name": NUT_UPS_NAME,
        "status": status,
        "onBattery": "OB" in status.split(),
        "lowBattery": "LB" in status.split(),
        "batteryCharge": _float(values, "battery.charge"),
        "batteryVoltage": _float(values, "battery.voltage"),
        "inputVoltage": _float(values, "input.voltage"),
        "outputVoltage": _float(values, "output.voltage"),
        "load": _float(values, "ups.load"),
        "temperature": _float(values, "ups.temperature"),
        "beeperStatus": values.get("ups.beeper.status"),
        "firmware": values.get("ups.firmware"),
        **compute_power(values),
        "runtimeSeconds": _runtime_seconds(values),
    }


async def get_ups_summary() -> dict | None:
    try:
        values = await asyncio.wait_for(_query_nut_vars(NUT_UPS_NAME), timeout=4.0)
    except Exception as exc:
        logger.warning("UPS stats unavailable: %s", exc)
        return None
    try:
        return build_summary(values)
    except Exception as exc:
        logger.warning("UPS summary could not be built: %s", exc)
        return None
