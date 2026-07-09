import asyncio
import logging
import os

logger = logging.getLogger(__name__)

NUT_HOST = os.getenv("NUT_HOST", "192.168.0.200")
NUT_PORT = int(os.getenv("NUT_PORT", "3493"))
NUT_USER = os.getenv("NUT_USER", "dashboard")
NUT_PASSWORD = os.getenv("NUT_PASSWORD", "")
NUT_UPS_NAME = os.getenv("NUT_UPS_NAME", "gembird")


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
        return float(raw)
    except ValueError:
        return None


async def get_ups_summary() -> dict | None:
    try:
        values = await asyncio.wait_for(_query_nut_vars(NUT_UPS_NAME), timeout=4.0)
    except Exception as exc:
        logger.warning("UPS stats unavailable: %s", exc)
        return None

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
    }
