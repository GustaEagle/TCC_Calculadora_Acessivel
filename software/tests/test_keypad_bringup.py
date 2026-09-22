"""The bring-up tool runs on the same scanner and polarity as the app.

Hardware-free: the sweep is fed by the recording fake IO and the toggle by the
fake gpiod module of test_keypad_matrix.py.
"""

import contextlib
import io
import sys
import unittest
from unittest import mock

from software.hw_platform.keypad_pinout import COL_BCM_PINS, ROW_BCM_PINS
from software.tests.test_keypad_matrix import FakeMatrixIO, fake_gpiod
from software.tools import keypad_bringup as tool


class InterruptingClock:
    """monotonic() that ends the scan with Ctrl-C after `stop_at` seconds."""

    def __init__(self, io: FakeMatrixIO, press_from: float, release_at: float, stop_at: float):
        self.now = 0.0
        self.io, self.press_from, self.release_at, self.stop_at = io, press_from, release_at, stop_at

    def __call__(self) -> float:
        self.now += 0.010
        if self.now >= self.stop_at:
            raise KeyboardInterrupt
        if self.press_from <= self.now < self.release_at:
            self.io.closed = {(3, 1)}  # SW9, "7"
        else:
            self.io.closed = set()
        return self.now


class RunScanTest(unittest.TestCase):
    def test_press_and_release_are_printed_with_every_field(self) -> None:
        fake = FakeMatrixIO()
        lines: list[str] = []
        seen = tool.run_scan(
            fake, settle_s=0, debounce_s=0.020,
            clock=InterruptingClock(fake, 0.05, 0.20, 0.40),
            sleep=lambda _s: None, out=lines.append,
        )
        events = [line for line in lines if "SW9" in line and "C3L1" in line]
        self.assertEqual(len(events), 2, lines)
        self.assertIn("pressionado", events[0])
        self.assertIn("solto", events[1])
        for text in ("'7'", "GPIO21", "GPIO9", "pino 40", "pino 21"):
            self.assertIn(text, events[0])
        self.assertEqual(seen, {"SW9"})
        self.assertEqual(fake.max_active, 1)

    def test_report_grid_marks_seen_missing_and_empty(self) -> None:
        text = tool.grid({"SW9"})
        self.assertIn("SW9", text)
        self.assertIn("—", text)
        self.assertIn("1 de 38", text)


class ListTest(unittest.TestCase):
    def test_list_prints_everything_without_touching_gpio(self) -> None:
        out = io.StringIO()
        with mock.patch.dict(sys.modules, {"gpiod": None}), contextlib.redirect_stdout(out):
            self.assertEqual(tool.main(["--list"]), 0)
        text = out.getvalue()
        self.assertEqual(text.count("SW"), 38)
        self.assertIn("L4 (Row4, GPIO27/pino 13", text)
        self.assertIn("C2L1, C2L2, C2L3, C4L4", text)


class ToggleTest(unittest.TestCase):
    def test_one_output_at_a_time_and_everything_floats_afterwards(self) -> None:
        gpiod = fake_gpiod()
        target = tool.LINES_BY_NAME["C3"]
        with mock.patch.dict(sys.modules, {"gpiod": gpiod, "gpiod.line": gpiod.line}):
            tool.run_toggle(target, cycles=2, sleep=lambda _s: None)

        request = gpiod.requests[0]
        first, last = request.configs[0], request.configs[-1]
        everything = set(ROW_BCM_PINS) | set(COL_BCM_PINS)
        self.assertEqual(set(first), everything)
        outputs = [bcm for bcm, s in first.items() if s.direction is gpiod.line.Direction.OUTPUT]
        self.assertEqual(outputs, [target.bcm])
        self.assertEqual(set(last), everything)
        for setting in last.values():
            self.assertEqual(
                (setting.direction, setting.bias),
                (gpiod.line.Direction.INPUT, gpiod.line.Bias.DISABLED),
            )
        self.assertTrue(request.released)
        self.assertEqual({offset for offset, _v in request.values}, {target.bcm})
        self.assertEqual(len(request.values), 4)  # 2 ciclos: alto, baixo, alto, baixo


if __name__ == "__main__":
    unittest.main()
