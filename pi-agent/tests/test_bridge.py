import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bridge  # noqa: E402

PROC_NET_HEADER = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
)


def proc_net_line(port: int, state: str = "0A") -> str:
    return (
        f"   0: 00000000:{port:04X} 00000000:0000 {state} 00000000:00000000 "
        "00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0\n"
    )


SOCAT_CMD = ["socat", "TCP-LISTEN:5555,fork,reuseaddr", "FILE:/dev/ttyACM0,b9600,raw,echo=0"]


class BridgeTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.dev_dir = os.path.join(self.root, "dev")
        os.makedirs(self.dev_dir)
        self.net_file = os.path.join(self.root, "tcp")
        self.write_net()
        self.state_file = os.path.join(self.root, "data", "bridge.json")
        self.processes: list[tuple[int, str, list[str]]] = []

    def write_net(self, *lines: str):
        with open(self.net_file, "w", encoding="ascii") as fh:
            fh.write(PROC_NET_HEADER + "".join(lines))

    def add_device(self, name: str):
        open(os.path.join(self.dev_dir, name), "w").close()

    def make(self, **kwargs) -> bridge.BridgeManager:
        defaults = dict(
            port=5555,
            baud=9600,
            state_file=self.state_file,
            dev_dir=self.dev_dir,
            proc_net_files=(self.net_file, os.path.join(self.root, "missing-tcp6")),
            process_lister=lambda: list(self.processes),
            start_timeout=0.5,
        )
        defaults.update(kwargs)
        return bridge.BridgeManager(**defaults)


class StatusTests(BridgeTestBase):
    def test_stopped_when_device_present_and_nothing_listening(self):
        self.add_device("ttyACM0")
        st = self.make().status()
        self.assertEqual(st["state"], "stopped")
        self.assertFalse(st["socatRunning"])
        self.assertTrue(st["serialPresent"])
        self.assertEqual(st["serialDevices"], [os.path.join(self.dev_dir, "ttyACM0")])

    def test_no_device_when_nothing_listening_and_no_serial(self):
        st = self.make().status()
        self.assertEqual(st["state"], "no_device")
        self.assertFalse(st["serialPresent"])

    def test_active_when_port_listening(self):
        self.add_device("ttyUSB1")
        self.write_net(proc_net_line(5555))
        st = self.make().status()
        self.assertEqual(st["state"], "active")
        self.assertTrue(st["listening"])

    def test_active_without_serial_is_still_active_but_flags_missing_device(self):
        self.write_net(proc_net_line(5555))
        st = self.make().status()
        self.assertEqual(st["state"], "active")
        self.assertFalse(st["serialPresent"])

    def test_non_listen_state_or_other_port_is_ignored(self):
        self.add_device("ttyACM0")
        self.write_net(proc_net_line(5555, state="01"), proc_net_line(5556))
        self.assertEqual(self.make().status()["state"], "stopped")

    def test_active_when_process_alive_even_if_port_not_yet_listening(self):
        self.add_device("ttyACM0")
        self.processes = [(4242, "socat", SOCAT_CMD)]
        st = self.make().status()
        self.assertEqual(st["state"], "active")
        self.assertEqual(st["pids"], [4242])

    def test_unrelated_processes_do_not_match(self):
        self.add_device("ttyACM0")
        self.processes = [
            (1, "socat", ["socat", "TCP-LISTEN:5556,fork", "FILE:/dev/ttyACM0"]),
            (2, "socat", ["socat", "TCP-LISTEN:55550,fork", "FILE:/dev/ttyACM0"]),
            (3, "python3", ["python3", "-c", "TCP-LISTEN:5555"]),
            (4, "socat", []),
            (5, "vim", ["vim", "TCP-LISTEN:5555"]),
        ]
        self.assertEqual(self.make().bridge_pids(), [])

    def test_python_fallback_bridge_is_recognised(self):
        self.processes = [(77, "python3", ["python3", "/tmp/ga_serial_bridge.py", "/dev/ttyACM0", "9600", "5555"])]
        self.assertEqual(self.make().bridge_pids(), [77])

    def test_only_tty_acm_and_usb_are_serial_devices(self):
        for name in ("ttyACM0", "ttyUSB0", "ttyS0", "ttyACM", "ttyACM0.bak", "tty1"):
            self.add_device(name)
        devs = [os.path.basename(d) for d in self.make().serial_devices()]
        self.assertEqual(devs, ["ttyACM0", "ttyUSB0"])


class PersistenceTests(BridgeTestBase):
    def test_desired_defaults_false_and_survives_restart(self):
        mgr = self.make()
        self.assertFalse(mgr.desired)
        mgr._save_desired(True)
        self.assertTrue(self.make().desired)
        with open(self.state_file, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"desired": True})

    def test_corrupt_state_file_falls_back_to_false(self):
        os.makedirs(os.path.dirname(self.state_file))
        with open(self.state_file, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertFalse(self.make().desired)


class StartStopTests(BridgeTestBase):
    def test_start_without_device_fails_and_does_not_set_desired(self):
        mgr = self.make()
        with self.assertRaises(bridge.BridgeError) as ctx:
            mgr.start()
        self.assertEqual(ctx.exception.code, "serial_missing")
        self.assertFalse(mgr.desired)

    def test_start_missing_binary(self):
        self.add_device("ttyACM0")
        mgr = self.make(socat_binary="definitely-not-socat-binary")
        with self.assertRaises(bridge.BridgeError) as ctx:
            mgr.start()
        self.assertEqual(ctx.exception.code, "socat_missing")
        self.assertFalse(mgr.desired)

    def test_start_process_dies_immediately(self):
        self.add_device("ttyACM0")
        # python recebe "TCP-LISTEN:..." como ficheiro de script e sai com erro.
        mgr = self.make(socat_binary=sys.executable)
        with self.assertRaises(bridge.BridgeError) as ctx:
            mgr.start()
        self.assertEqual(ctx.exception.code, "start_failed")
        self.assertFalse(mgr.desired)

    def test_start_builds_argv_list_without_shell(self):
        self.add_device("ttyACM0")
        self.write_net(proc_net_line(5555))  # simula a porta a ouvir após o arranque
        mgr = self.make()
        mgr.is_listening = mock.Mock(side_effect=[False, True, True])
        fake = mock.Mock()
        fake.poll.return_value = None
        with mock.patch("bridge.subprocess.Popen", return_value=fake) as popen:
            mgr.start()
        args, kwargs = popen.call_args
        self.assertEqual(
            args[0],
            [
                "socat",
                "TCP-LISTEN:5555,fork,reuseaddr",
                f"FILE:{os.path.join(self.dev_dir, 'ttyACM0')},b9600,raw,echo=0",
            ],
        )
        self.assertNotIn("shell", kwargs)
        self.assertTrue(kwargs["start_new_session"])
        self.assertTrue(mgr.desired)

    def test_start_when_already_running_does_not_spawn(self):
        self.add_device("ttyACM0")
        self.write_net(proc_net_line(5555))
        mgr = self.make()
        with mock.patch("bridge.subprocess.Popen") as popen:
            st = mgr.start()
        popen.assert_not_called()
        self.assertEqual(st["state"], "active")
        self.assertTrue(mgr.desired)

    def test_stop_terminates_matching_processes_and_clears_desired(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(lambda: child.poll() is None and child.kill())
        self.add_device("ttyACM0")
        self.processes = []

        def lister():
            return [(child.pid, "socat", SOCAT_CMD)] if child.poll() is None else []

        mgr = self.make(process_lister=lister)
        mgr._save_desired(True)
        st = mgr.stop()
        self.assertIsNotNone(child.poll())
        self.assertFalse(mgr.desired)
        self.assertEqual(st["state"], "stopped")

    def test_stop_is_idempotent(self):
        self.add_device("ttyACM0")
        st = self.make().stop()
        self.assertEqual(st["state"], "stopped")

    def test_does_not_match_own_pid(self):
        self.processes = [(os.getpid(), "socat", SOCAT_CMD)]
        self.assertEqual(self.make().bridge_pids(), [])


class ReconcileTests(BridgeTestBase):
    def test_noop_when_not_desired(self):
        self.add_device("ttyACM0")
        mgr = self.make()
        with mock.patch("bridge.subprocess.Popen") as popen:
            mgr.reconcile()
        popen.assert_not_called()

    def test_noop_when_desired_but_no_device(self):
        mgr = self.make()
        mgr._save_desired(True)
        with mock.patch("bridge.subprocess.Popen") as popen:
            mgr.reconcile()
        popen.assert_not_called()

    def test_respawns_when_desired_and_dead_and_device_present(self):
        self.add_device("ttyACM0")
        mgr = self.make()
        mgr._save_desired(True)
        with mock.patch.object(mgr, "_spawn") as spawn:
            mgr.reconcile()
        spawn.assert_called_once()

    def test_does_not_respawn_when_already_listening(self):
        self.add_device("ttyACM0")
        self.write_net(proc_net_line(5555))
        mgr = self.make()
        mgr._save_desired(True)
        with mock.patch.object(mgr, "_spawn") as spawn:
            mgr.reconcile()
        spawn.assert_not_called()


class EnvTests(unittest.TestCase):
    def test_invalid_values_fall_back_to_defaults(self):
        with mock.patch.dict(os.environ, {"BRIDGE_PORT": "abc", "BRIDGE_BAUD": "12345"}):
            self.assertEqual(bridge.env_port(), 5555)
            self.assertEqual(bridge.env_baud(), 9600)
        with mock.patch.dict(os.environ, {"BRIDGE_PORT": "80", "BRIDGE_BAUD": "115200"}):
            self.assertEqual(bridge.env_port(), 5555)
            self.assertEqual(bridge.env_baud(), 115200)

    def test_enabled_flag(self):
        with mock.patch.dict(os.environ, {"BRIDGE_ENABLED": "true"}):
            self.assertTrue(bridge.env_enabled())
        with mock.patch.dict(os.environ, {"BRIDGE_ENABLED": ""}):
            self.assertFalse(bridge.env_enabled())


if __name__ == "__main__":
    unittest.main()
