"""RF-05/RF-11: the keypad matrix scanner, without a Pi and without gpiod.

The electrical rules validated on the bench (one column HIGH at a time, rows
with pull-down, never a row as output, everything floating on exit) are the
part that can burn a pin or produce phantom keys, so each one is pinned here:
the pure sweep/debounce logic against a recording fake IO, and GpiodMatrixIO
against a fake `gpiod` module that records every line configuration.
"""

import enum
import logging
import sys
import threading
import types
import unittest
from unittest import mock

from software.hw_platform import keypad_matrix as km
from software.hw_platform.keypad_pinout import (
    COL_BCM_PINS,
    COL_LINES,
    ROW_BCM_PINS,
    ROW_LINES,
)


class FakeMatrixIO:
    """Simulates the grid: `closed` holds the (col, row) switches held down."""

    def __init__(self, closed=()) -> None:
        self.closed = set(closed)
        self.active: list[int] = []
        self.calls: list[tuple] = []
        self.max_active = 0
        self.fail_read = False
        self.closed_io = False

    def drive_column(self, bcm: int) -> None:
        self.calls.append(("drive", bcm))
        self.active.append(bcm)
        self.max_active = max(self.max_active, len(self.active))

    def float_column(self, bcm: int) -> None:
        self.calls.append(("float", bcm))
        self.active.remove(bcm)

    def read_rows(self) -> tuple[bool, ...]:
        self.calls.append(("read", tuple(self.active)))
        if self.fail_read:
            raise OSError("ioctl falhou")
        col = COL_BCM_PINS.index(self.active[0])
        return tuple((col, row) in self.closed for row in range(len(ROW_LINES)))

    def float_all(self) -> None:
        self.calls.append(("float_all",))
        self.active.clear()

    def close(self) -> None:
        self.calls.append(("close",))
        self.closed_io = True


class ScanOnceTest(unittest.TestCase):
    def test_closed_switch_is_read_at_its_coordinate(self) -> None:
        io = FakeMatrixIO(closed={(3, 3)})  # SW21, keycap "1"
        self.assertEqual(km.scan_once(io, sleep=lambda _s: None), {(3, 3)})

    def test_only_one_column_is_ever_driven(self) -> None:
        io = FakeMatrixIO(closed={(0, 0), (6, 5)})
        km.scan_once(io, sleep=lambda _s: None)
        self.assertEqual(io.max_active, 1)
        self.assertEqual(io.active, [])

    def test_rows_are_read_only_with_exactly_one_column_active(self) -> None:
        io = FakeMatrixIO()
        km.scan_once(io, sleep=lambda _s: None)
        reads = [call for call in io.calls if call[0] == "read"]
        self.assertEqual(len(reads), len(COL_LINES))
        for _name, active in reads:
            self.assertEqual(len(active), 1)

    def test_column_floats_before_the_next_one_is_driven(self) -> None:
        io = FakeMatrixIO()
        km.scan_once(io, sleep=lambda _s: None)
        kinds = [call[0] for call in io.calls]
        self.assertEqual(kinds, ["drive", "read", "float"] * len(COL_LINES))

    def test_settle_time_is_waited_after_driving(self) -> None:
        io = FakeMatrixIO()
        waits = []
        km.scan_once(io, settle_s=0.001, sleep=waits.append)
        self.assertEqual(waits, [0.001] * len(COL_LINES))

    def test_failed_read_still_floats_the_column(self) -> None:
        io = FakeMatrixIO()
        io.fail_read = True
        with self.assertRaises(OSError):
            km.scan_once(io, sleep=lambda _s: None)
        self.assertEqual(io.calls[-1], ("float", COL_BCM_PINS[0]))
        self.assertEqual(io.active, [])


class DebouncerTest(unittest.TestCase):
    SW9 = frozenset({(3, 1)})  # C3L1, keycap "7"
    NONE = frozenset()

    def feed(self, debouncer, samples):
        events = []
        for now, closed in samples:
            events.extend(debouncer.update(now, closed))
        return events

    def test_stable_press_gives_one_event_with_every_field(self) -> None:
        events = self.feed(km.Debouncer(0.020), [
            (0.000, self.SW9), (0.010, self.SW9), (0.020, self.SW9), (0.030, self.SW9),
        ])
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(
            (event.keycap, event.coord, event.switch, event.state),
            ("7", "C3L1", "SW9", "pressionado"),
        )
        self.assertEqual((event.col_bcm, event.row_bcm), (21, 9))

    def test_bounce_within_the_window_gives_one_press(self) -> None:
        events = self.feed(km.Debouncer(0.020), [
            (0.000, self.SW9), (0.003, self.NONE), (0.006, self.SW9),
            (0.009, self.NONE), (0.012, self.SW9), (0.022, self.SW9), (0.040, self.SW9),
        ])
        self.assertEqual([e.state for e in events], ["pressionado"])

    def test_release_gives_one_released_event(self) -> None:
        debouncer = km.Debouncer(0.020)
        self.feed(debouncer, [(0.000, self.SW9), (0.025, self.SW9)])
        events = self.feed(debouncer, [
            (0.050, self.NONE), (0.060, self.NONE), (0.075, self.NONE), (0.090, self.NONE),
        ])
        self.assertEqual([(e.switch, e.state) for e in events], [("SW9", "solto")])
        self.assertEqual(debouncer.pressed, frozenset())

    def test_pulse_shorter_than_the_window_is_ignored(self) -> None:
        events = self.feed(km.Debouncer(0.020), [
            (0.000, self.SW9), (0.010, self.NONE), (0.030, self.NONE), (0.060, self.NONE),
        ])
        self.assertEqual(events, [])

    def test_simultaneous_keys_each_get_their_event(self) -> None:
        both = frozenset({(0, 5), (0, 1)})  # Ctrl (C0L5) + sen (C0L1)
        events = self.feed(km.Debouncer(0.020), [(0.000, both), (0.025, both)])
        self.assertEqual(sorted(e.keycap for e in events), ["Ctrl", "sen"])

    def test_empty_position_never_becomes_a_key(self) -> None:
        empty = frozenset({(2, 1)})
        debouncer = km.Debouncer(0.020)
        with self.assertLogs(km.logger, level=logging.WARNING) as logs:
            events = self.feed(debouncer, [(0.000, empty), (0.030, empty), (0.060, empty)])
        self.assertEqual(events, [])
        # Um aviso por ocorrência contínua, não um por varredura.
        self.assertEqual(len(logs.records), 1)
        self.assertIn("C2L1", logs.output[0])


class FakeLineSettings:
    def __init__(self, direction=None, bias=None, output_value=None) -> None:
        self.direction, self.bias, self.output_value = direction, bias, output_value


class FakeRequest:
    def __init__(self, config: dict, rows_high=()) -> None:
        self.configs = [dict(config)]
        self.rows_high = set(rows_high)
        self.released = False
        self.fail_reconfigure = False

    def reconfigure_lines(self, config: dict) -> None:
        if self.fail_reconfigure:
            raise OSError("ioctl falhou")
        self.configs.append(dict(config))

    def get_values(self, offsets):
        line = sys.modules["gpiod.line"]
        return [line.Value.ACTIVE if o in self.rows_high else line.Value.INACTIVE for o in offsets]

    def set_value(self, offset, value) -> None:
        self.values = getattr(self, "values", [])
        self.values.append((offset, value))

    def release(self) -> None:
        self.released = True


def fake_gpiod(label="pinctrl-bcm2711", used=None):
    """A stand-in for the libgpiod v2 Python package."""
    line = types.ModuleType("gpiod.line")
    line.Direction = enum.Enum("Direction", "INPUT OUTPUT AS_IS")
    line.Bias = enum.Enum("Bias", "DISABLED PULL_UP PULL_DOWN AS_IS")
    line.Value = enum.Enum("Value", "INACTIVE ACTIVE")

    gpiod = types.ModuleType("gpiod")
    gpiod.line = line
    gpiod.LineSettings = FakeLineSettings
    gpiod.requests = []
    used = used or {}

    class Chip:
        def __init__(self, path) -> None:
            self.path = path

        def get_info(self):
            return types.SimpleNamespace(label=label)

        def get_line_info(self, offset):
            return types.SimpleNamespace(used=offset in used, consumer=used.get(offset, ""))

        def close(self) -> None:
            pass

    def request_lines(path, consumer, config):
        request = FakeRequest(config)
        request.consumer = consumer
        gpiod.requests.append(request)
        return request

    gpiod.Chip = Chip
    gpiod.request_lines = request_lines
    return gpiod


class GpiodMatrixIOTest(unittest.TestCase):
    def open(self, **fake_kwargs):
        gpiod = fake_gpiod(**fake_kwargs)
        patcher = mock.patch.dict(sys.modules, {"gpiod": gpiod, "gpiod.line": gpiod.line})
        patcher.start()
        self.addCleanup(patcher.stop)
        exists = mock.patch.object(km.os.path, "exists", return_value=True)
        exists.start()
        self.addCleanup(exists.stop)
        return gpiod, km.GpiodMatrixIO("/dev/gpiochip0")

    def assert_safe(self, config: dict, line) -> None:
        self.assertEqual(set(config), set(ROW_BCM_PINS) | set(COL_BCM_PINS),
                         "cada configuração tem de descrever as 13 linhas")
        outputs = [bcm for bcm, s in config.items() if s.direction is line.Direction.OUTPUT]
        self.assertLessEqual(len(outputs), 1, "duas colunas em saída")
        self.assertFalse(set(outputs) & set(ROW_BCM_PINS), "linha em saída")

    def test_request_is_made_once_with_rows_pulled_down_and_columns_floating(self) -> None:
        gpiod, _io = self.open()
        self.assertEqual(len(gpiod.requests), 1)
        request = gpiod.requests[0]
        self.assertEqual(request.consumer, km.CONSUMER)
        config = request.configs[0]
        self.assert_safe(config, gpiod.line)
        for bcm in ROW_BCM_PINS:
            self.assertEqual(
                (config[bcm].direction, config[bcm].bias),
                (gpiod.line.Direction.INPUT, gpiod.line.Bias.PULL_DOWN),
            )
        for bcm in COL_BCM_PINS:
            self.assertEqual(
                (config[bcm].direction, config[bcm].bias),
                (gpiod.line.Direction.INPUT, gpiod.line.Bias.DISABLED),
            )

    def test_every_sweep_configuration_is_complete_and_safe(self) -> None:
        gpiod, io = self.open()
        km.scan_once(io, sleep=lambda _s: None)
        request = gpiod.requests[0]
        for config in request.configs:
            self.assert_safe(config, gpiod.line)
        driven = [
            bcm for config in request.configs for bcm, s in config.items()
            if s.direction is gpiod.line.Direction.OUTPUT
        ]
        self.assertEqual(driven, list(COL_BCM_PINS))

    def test_active_column_is_driven_high_without_bias(self) -> None:
        gpiod, io = self.open()
        io.drive_column(COL_BCM_PINS[3])
        setting = gpiod.requests[0].configs[-1][COL_BCM_PINS[3]]
        self.assertEqual(setting.output_value, gpiod.line.Value.ACTIVE)
        self.assertEqual(setting.bias, gpiod.line.Bias.DISABLED)

    def test_second_column_is_refused_while_the_first_is_active(self) -> None:
        _gpiod, io = self.open()
        io.drive_column(COL_BCM_PINS[0])
        with self.assertRaises(RuntimeError):
            io.drive_column(COL_BCM_PINS[1])

    def test_rows_cannot_be_driven(self) -> None:
        _gpiod, io = self.open()
        with self.assertRaises(ValueError):
            io.drive_column(ROW_BCM_PINS[0])

    def test_rows_are_read_in_one_call_in_row_order(self) -> None:
        gpiod, io = self.open()
        gpiod.requests[0].rows_high = {ROW_BCM_PINS[3]}  # L3 = GPIO17
        io.drive_column(COL_BCM_PINS[3])
        self.assertEqual(io.read_rows(), (False, False, False, True, False, False))

    def test_close_floats_all_thirteen_lines_then_releases(self) -> None:
        gpiod, io = self.open()
        io.drive_column(COL_BCM_PINS[2])
        io.close()
        request = gpiod.requests[0]
        last = request.configs[-1]
        self.assertEqual(set(last), set(ROW_BCM_PINS) | set(COL_BCM_PINS))
        for setting in last.values():
            self.assertEqual(
                (setting.direction, setting.bias),
                (gpiod.line.Direction.INPUT, gpiod.line.Bias.DISABLED),
            )
        self.assertTrue(request.released)
        io.close()  # idempotente

    def test_close_releases_even_if_floating_fails(self) -> None:
        gpiod, io = self.open()
        gpiod.requests[0].fail_reconfigure = True
        with self.assertRaises(OSError):
            io.close()
        self.assertTrue(gpiod.requests[0].released)

    def test_wrong_chip_is_refused_before_requesting(self) -> None:
        gpiod = fake_gpiod(label="pinctrl-rp1")
        with mock.patch.dict(sys.modules, {"gpiod": gpiod, "gpiod.line": gpiod.line}), \
                mock.patch.object(km.os.path, "exists", return_value=True):
            with self.assertRaises(km.MatrixOpenError):
                km.GpiodMatrixIO()
        self.assertEqual(gpiod.requests, [])

    def test_busy_line_is_named_and_nothing_is_requested(self) -> None:
        gpiod = fake_gpiod(used={14: "serial0"})
        with mock.patch.dict(sys.modules, {"gpiod": gpiod, "gpiod.line": gpiod.line}), \
                mock.patch.object(km.os.path, "exists", return_value=True):
            with self.assertRaises(km.MatrixOpenError) as ctx:
                km.GpiodMatrixIO()
        self.assertIn("C6 (GPIO14)", str(ctx.exception))
        self.assertIn("serial0", str(ctx.exception))
        self.assertEqual(gpiod.requests, [])

    def test_missing_package_means_no_matrix(self) -> None:
        with mock.patch.dict(sys.modules, {"gpiod": None}):
            with self.assertRaises(km.MatrixUnavailable):
                km.GpiodMatrixIO()


class MatrixKeyboardTest(unittest.TestCase):
    def make(self, io, clock):
        keyboard = km.MatrixKeyboard(
            io, settle_s=0, debounce_s=0.020, pause_s=0, clock=clock, sleep=lambda _s: None
        )
        self.addCleanup(keyboard.close)
        return keyboard

    def test_events_reach_the_attached_sink(self) -> None:
        io = FakeMatrixIO(closed={(3, 1)})
        ticks = iter(i * 0.010 for i in range(10_000))
        keyboard = self.make(io, clock=lambda: next(ticks, 100.0))
        got = threading.Event()
        events = []

        def sink(event):
            events.append(event)
            got.set()

        keyboard.attach(sink)
        keyboard.start()
        self.assertTrue(got.wait(2.0))
        self.assertEqual((events[0].keycap, events[0].state), ("7", "pressionado"))

    def test_detached_keyboard_drops_events(self) -> None:
        io = FakeMatrixIO(closed={(3, 1)})
        keyboard = self.make(io, clock=lambda: 0.0)
        events = []
        keyboard.attach(events.append)
        keyboard.detach()
        keyboard._deliver(km._event((3, 1), True, 0.0))
        self.assertEqual(events, [])

    def test_close_floats_everything_and_closes_the_io(self) -> None:
        io = FakeMatrixIO()
        keyboard = self.make(io, clock=lambda: 0.0)
        keyboard.start()
        keyboard.close()
        self.assertFalse(keyboard.running)
        self.assertIn(("float_all",), io.calls)
        self.assertEqual(io.calls[-1], ("close",))
        keyboard.close()  # idempotente
        self.assertEqual(io.calls.count(("close",)), 1)

    def test_io_error_stops_the_sweep_instead_of_spinning(self) -> None:
        io = FakeMatrixIO()
        io.fail_read = True
        keyboard = self.make(io, clock=lambda: 0.0)
        with self.assertLogs(km.logger, level=logging.ERROR):
            keyboard.start()
            keyboard._thread.join(2.0)
        self.assertFalse(keyboard.running)
        self.assertEqual(io.active, [])
        self.assertIn(("float_all",), io.calls)

    def test_open_without_gpiod_returns_none(self) -> None:
        with mock.patch.dict(sys.modules, {"gpiod": None}):
            with self.assertLogs(km.logger, level=logging.INFO):
                self.assertIsNone(km.MatrixKeyboard.open())


if __name__ == "__main__":
    unittest.main()
