"""RF-05: physical keypad presses drive both fronts like the PC keyboard does.

Builds the real Tk fronts (Xvfb in the CI, like test_history_via_keyboard.py)
with a fake matrix keyboard, and feeds events through the same pump the
scanner thread uses. The point is the Ctrl/Shift functions: from the matrix,
every key carries its full catalogue entry, not just the primary token.
"""

import contextlib
import unittest
from unittest import mock

from software.hw_platform.keypad_matrix import KeyEvent
from software.hw_platform.keypad_pinout import SWITCHES
from software.ui.shared.keypad import NO_FUNCTION_SPEECH


def _load(front: str):
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


class FakeKeyboard:
    def __init__(self) -> None:
        self.sink = None

    def attach(self, sink) -> None:
        self.sink = sink

    def detach(self) -> None:
        self.sink = None


def press(app, keyboard: FakeKeyboard, *keycaps: str) -> None:
    for keycap in keycaps:
        sw = next(sw for sw in SWITCHES if sw.keycap == keycap)
        keyboard.sink(KeyEvent(keycap, sw.coord, sw.switch, True, 0, 0, 0.0))
        keyboard.sink(KeyEvent(keycap, sw.coord, sw.switch, False, 0, 0, 0.0))
    app.matrix_input.tick()


class MatrixKeysInFrontsTest(unittest.TestCase):
    FRONTS = ("lcd", "hdmi")

    @contextlib.contextmanager
    def front(self, name: str):
        """One front at a time: ttkbootstrap cannot hold two live windows."""
        keyboard = FakeKeyboard()
        app = _load(name)(keypad_matrix=keyboard)
        app.speech = mock.MagicMock()
        app.matrix_input.start()
        try:
            yield app, keyboard
        finally:
            app.root.destroy()

    def test_digits_and_operators_reach_the_expression(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "+", "2")
                self.assertEqual(app.state.expression, "7+2")

    def test_ctrl_then_sen_inserts_arc_sine(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "Ctrl", "sen")
                self.assertEqual(app.state.expression, "asin(")
                self.assertFalse(app.ctrl_active, "o Ctrl tem de ser consumido")

    def test_shift_then_log_inserts_log_in_base(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "Shift", "log")
                self.assertEqual(app.state.expression, "logbase(")

    def test_shift_then_slash_toggles_the_angle_mode(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "Shift", "/")
                self.assertEqual(app.state.angle_mode, "rad")
                # Indicador e voz acompanham o modo: quem não vê a tela só tem a voz.
                self.assertEqual(app.mode_var.get(), "RAD")
                app.speech.say.assert_called_with("Modo rad")
                self.assertEqual(app.state.expression, "")
                self.assertFalse(app.shift_active, "o Shift tem de ser consumido")

    def test_question_mark_is_announced_and_types_nothing(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "?")
                self.assertEqual(app.state.expression, "7")
                app.speech.say.assert_called_with(NO_FUNCTION_SPEECH)

    def test_run_stops_the_pump_when_the_window_closes(self) -> None:
        keyboard = FakeKeyboard()
        app = _load("lcd")(keypad_matrix=keyboard)
        app.speech = mock.MagicMock()
        app.root.after(50, app.root.destroy)
        app.run()
        self.assertIsNone(keyboard.sink, "a janela fechou mas o front ficou ligado à matriz")

    def test_front_without_matrix_has_no_pump(self) -> None:
        app = _load("lcd")()
        app.speech = mock.MagicMock()
        try:
            self.assertIsNone(app.matrix_input)
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
