"""Gestão do bridge Arduino <-> TCP (socat) no Raspberry Pi 1.

Equivalente ao que o GardenAssistant espera em ARDUINO_SOCAT_HOST:5555
(ver GardenAssistant/backend/scripts/runArduino.sh):

    socat TCP-LISTEN:5555,fork,reuseaddr FILE:/dev/ttyACM0,b9600,raw,echo=0

Notas de segurança:
  * nenhum input do cliente chega a este módulo (as rotas são start/stop sem
    parâmetros); porta e baud vêm de variáveis de ambiente validadas;
  * o socat é lançado com argv em lista (sem shell) e o device serial só é
    aceite se bater no padrão /dev/tty(ACM|USB)<n>;
  * o estado do bridge é lido sem abrir o device serial nem ligar à porta TCP
    (abrir a porta serial faz reset a muitos Arduinos e o bridge só aceita um
    cliente de cada vez) — lê-se /proc/net/tcp e a lista de processos.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from typing import Callable, Iterable

import psutil

logger = logging.getLogger("pi-agent.bridge")

_SERIAL_NAME_RE = re.compile(r"^tty(ACM|USB)\d+$")
_ALLOWED_BAUDS = (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)

ProcessLister = Callable[[], Iterable[tuple[int, str, list[str]]]]


class BridgeError(Exception):
    """Erro de negócio do bridge. `code` mapeia para o estado HTTP no server."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r inválido, a usar %d", name, raw, default)
        return default
    if not minimum <= value <= maximum:
        logger.warning("%s=%d fora do intervalo %d-%d, a usar %d", name, value, minimum, maximum, default)
        return default
    return value


def env_enabled() -> bool:
    return os.getenv("BRIDGE_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def env_port() -> int:
    return _env_int("BRIDGE_PORT", 5555, 1024, 65535)


def env_baud() -> int:
    baud = _env_int("BRIDGE_BAUD", 9600, 1200, 115200)
    if baud not in _ALLOWED_BAUDS:
        logger.warning("BRIDGE_BAUD=%d não suportado, a usar 9600", baud)
        return 9600
    return baud


def _default_process_lister() -> Iterable[tuple[int, str, list[str]]]:
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        info = proc.info
        yield info["pid"], info.get("name") or "", info.get("cmdline") or []


class BridgeManager:
    def __init__(
        self,
        port: int = 5555,
        baud: int = 9600,
        state_file: str | None = None,
        dev_dir: str = "/dev",
        proc_net_files: tuple[str, ...] = ("/proc/net/tcp", "/proc/net/tcp6"),
        process_lister: ProcessLister | None = None,
        socat_binary: str = "socat",
        start_timeout: float = 3.0,
    ):
        if baud not in _ALLOWED_BAUDS:
            raise ValueError(f"baud {baud} não suportado")
        self.port = port
        self.baud = baud
        self._state_file = state_file
        self._dev_dir = dev_dir
        self._proc_net_files = proc_net_files
        self._process_lister = process_lister or _default_process_lister
        self._socat_binary = socat_binary
        self._start_timeout = start_timeout
        self._lock = threading.RLock()
        self._proc: subprocess.Popen | None = None
        self._self_pid = os.getpid()
        self._listen_re = re.compile(rf"^TCP[46]?-LISTEN:{port}(,.*)?$")
        self._desired = self._load_desired()

    # ── Estado persistido (intenção do utilizador) ───────────────────────────

    def _load_desired(self) -> bool:
        if not self._state_file:
            return False
        try:
            with open(self._state_file, encoding="utf-8") as fh:
                return bool(json.load(fh).get("desired", False))
        except FileNotFoundError:
            return False
        except (OSError, ValueError) as exc:
            logger.warning("Estado do bridge ilegível (%s): %s", self._state_file, exc)
            return False

    def _save_desired(self, desired: bool) -> None:
        self._desired = desired
        if not self._state_file:
            return
        try:
            directory = os.path.dirname(self._state_file) or "."
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".bridge-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"desired": desired}, fh)
            os.replace(tmp_path, self._state_file)
        except OSError as exc:
            logger.warning("Não foi possível guardar o estado do bridge: %s", exc)

    @property
    def desired(self) -> bool:
        return self._desired

    # ── Leitura de estado (sem tocar no device nem na porta) ─────────────────

    def serial_devices(self) -> list[str]:
        try:
            names = os.listdir(self._dev_dir)
        except OSError:
            return []
        return [
            os.path.join(self._dev_dir, name)
            for name in sorted(names)
            if _SERIAL_NAME_RE.match(name)
        ]

    def is_listening(self) -> bool:
        wanted = f"{self.port:04X}"
        for path in self._proc_net_files:
            try:
                with open(path, encoding="ascii") as fh:
                    next(fh, None)  # cabeçalho
                    for line in fh:
                        fields = line.split()
                        if len(fields) < 4:
                            continue
                        local, state = fields[1], fields[3]
                        if state == "0A" and local.rsplit(":", 1)[-1].upper() == wanted:
                            return True
            except OSError:
                continue
        return False

    def _is_bridge_cmdline(self, name: str, cmdline: list[str]) -> bool:
        if not cmdline:
            return False
        if name == "socat" or os.path.basename(cmdline[0]) == "socat":
            return any(self._listen_re.match(arg) for arg in cmdline[1:])
        # Fallback Python que o GardenAssistant instala quando não há socat.
        return (
            any(os.path.basename(arg) == "ga_serial_bridge.py" for arg in cmdline[1:3])
            and cmdline[-1] == str(self.port)
        )

    def bridge_pids(self) -> list[int]:
        pids = []
        try:
            for pid, name, cmdline in self._process_lister():
                if pid != self._self_pid and self._is_bridge_cmdline(name, list(cmdline)):
                    pids.append(pid)
        except Exception as exc:  # psutil pode falhar em condições de corrida
            logger.warning("Falha a listar processos: %s", exc)
        return sorted(pids)

    def _managed_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def status(self) -> dict:
        with self._lock:
            devices = self.serial_devices()
            listening = self.is_listening()
            pids = self.bridge_pids()
            running = listening or bool(pids)
            if running:
                state = "active"
            elif not devices:
                state = "no_device"
            else:
                state = "stopped"
            return {
                "enabled": True,
                "state": state,
                "socatRunning": running,
                "listening": listening,
                "serialPresent": bool(devices),
                "serialDevices": devices,
                "port": self.port,
                "baud": self.baud,
                "desired": self._desired,
                "managed": self._managed_alive(),
                "pids": pids,
            }

    # ── Ações ────────────────────────────────────────────────────────────────

    def start(self) -> dict:
        with self._lock:
            if not (self.is_listening() or self.bridge_pids()):
                self._spawn()
            self._save_desired(True)
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            # Primeiro a intenção, para o supervisor não o relançar a meio.
            self._save_desired(False)
            self._terminate_all()
            return self.status()

    def reconcile(self) -> None:
        """Chamado periodicamente: se o utilizador quer o bridge ligado mas ele
        morreu (reinício do agente, Arduino religado), volta a lançá-lo."""
        with self._lock:
            if self._proc is not None and self._proc.poll() is not None:
                self._proc = None
            if not self._desired:
                return
            if self.is_listening() or self.bridge_pids():
                return
            if not self.serial_devices():
                return
            try:
                self._spawn()
                logger.info("Bridge relançado pelo supervisor")
            except BridgeError as exc:
                logger.warning("Supervisor não conseguiu lançar o bridge: %s", exc.message)

    def _spawn(self) -> None:
        devices = self.serial_devices()
        if not devices:
            raise BridgeError("serial_missing", "Arduino não detetado (sem /dev/ttyACM* nem /dev/ttyUSB*)")
        device = devices[0]
        argv = [
            self._socat_binary,
            f"TCP-LISTEN:{self.port},fork,reuseaddr",
            f"FILE:{device},b{self.baud},raw,echo=0",
        ]
        log_handle = self._open_log()
        try:
            self._proc = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=log_handle,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise BridgeError("socat_missing", "socat não está instalado no agente") from exc
        except OSError as exc:
            logger.error("Falha ao lançar socat: %s", exc)
            raise BridgeError("start_failed", "Não foi possível lançar o socat") from exc
        finally:
            if log_handle not in (None, subprocess.DEVNULL):
                log_handle.close()

        deadline = time.monotonic() + self._start_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                code = self._proc.returncode
                self._proc = None
                logger.error("socat terminou ao arrancar (exit %s); ver %s", code, self._log_path() or "-")
                raise BridgeError("start_failed", "O socat terminou ao arrancar (ver log do agente)")
            if self.is_listening():
                logger.info("Bridge lançado: %s -> %s @ %d", self.port, device, self.baud)
                return
            time.sleep(0.1)
        # Vivo mas ainda sem porta: não é erro fatal, o próximo status mostra a verdade.
        logger.warning("socat vivo mas a porta %d ainda não está a ouvir", self.port)

    def _log_path(self) -> str | None:
        if not self._state_file:
            return None
        return os.path.join(os.path.dirname(self._state_file) or ".", "bridge-socat.log")

    def _open_log(self):
        path = self._log_path()
        if path is None:
            return subprocess.DEVNULL
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            return open(path, "wb")
        except OSError:
            return subprocess.DEVNULL

    def _terminate_all(self) -> None:
        pids = self.bridge_pids()
        procs = []
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                procs.append(proc)
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                logger.error("Sem permissão para terminar o processo %d do bridge", pid)
                raise BridgeError("stop_failed", "Sem permissão para terminar o socat")
        if procs:
            _gone, alive = psutil.wait_procs(procs, timeout=3)
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            if alive:
                psutil.wait_procs(alive, timeout=2)
        if self._proc is not None:
            try:
                self._proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            self._proc = None
        if self.is_listening() and not self.bridge_pids():
            logger.warning("A porta %d continua a ouvir mas não por um processo de bridge conhecido", self.port)
