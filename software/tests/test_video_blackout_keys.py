"""video-blackout 4.x: Ctrl + AC, and the same behaviour on both fronts.

The matrix has no free key, so the command is AC's Ctrl function (design D4) -
Ctrl and then Esc on a PC. The fronts are real Tk windows (as in
test_history_via_keyboard.py; Xvfb in the CI), but the applier that would
reach xrandr is a double: what is under test is the wiring - which keys, what
is spoken, what state survives - not the X server.
"""

import contextlib
import unittest
from unittest import mock

from software.core.engine import CalculationEngine
from software.hw_platform.display import DisplayMode
from software.hw_platform.keyboard import KeyboardAdapter
from software.ui.shared import video_blackout
from software.ui.shared.keypad import LEFT_BUTTONS, RIGHT_BUTTONS, SPOKEN_TOKEN_NAMES, spoken_token
from software.ui.shared.video_blackout import BLACKOUT_TOKEN

FRONTS = ("lcd", "hdmi")

_UNSET = object()


def _load(front: str):
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


def ctrl_then_ac(app) -> None:
    """As it arrives from a keyboard (Ctrl, then AC/Esc): no 'secondary'."""
    app._handle_token("Ctrl", None, None)
    app._handle_token("AC", None, None)


class Applier:
    """Stands in for app.make_video_applier: answers `panel`, counts calls."""

    def __init__(self, panel=DisplayMode.LCD) -> None:
        self.panel = panel
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.panel


@contextlib.contextmanager
def front_app(front: str, panel=DisplayMode.LCD, applier=_UNSET, **kwargs):
    """One front at a time, destroyed on exit.

    ttkbootstrap keeps its Style in a singleton bound to one Tk interpreter, so
    a second window built while the first is alive comes up without its theme -
    the same reason every front resets it (tk_session.py).
    """
    app = _load(front)(speech=mock.MagicMock(), **kwargs)
    try:
        if applier is _UNSET:
            app.apply_video = Applier(panel)
        yield app
    finally:
        app.root.destroy()


def spoken(app) -> list[str]:
    return [call.args[0] for call in app.speech.interrupt_and_say.call_args_list]


class BlackoutShortcutCatalogueTest(unittest.TestCase):
    """4.1/4.2"""

    def keys(self) -> list[tuple]:
        return [key for row in LEFT_BUTTONS + RIGHT_BUTTONS for key in row]

    def test_the_command_is_the_ctrl_function_of_ac(self) -> None:
        carriers = [label for label, _p, ctrl, shift in self.keys() if BLACKOUT_TOKEN in (ctrl, shift)]
        self.assertEqual(carriers, ["AC"])
        self.assertNotIn(BLACKOUT_TOKEN, [primary for _l, primary, _c, _s in self.keys()])

    def test_no_key_missing_from_the_matrix_is_left_in_the_catalogue(self) -> None:
        """The '?' of the KLE exports does not exist on the 6x7 matrix."""
        self.assertNotIn("?", [label for label, *_tokens in self.keys()])

    def test_the_command_does_not_collide_with_the_math_catalogue(self) -> None:
        """Spec: no operator, function, digit or separator of PRD §5 is displaced."""
        ac = next(key for key in self.keys() if key[0] == "AC")
        self.assertEqual(ac[1], "AC", "AC perdeu a sua funcao primaria")
        others = {token for key in self.keys() if key[0] != "AC" for token in key[1:] if token}
        self.assertNotIn(BLACKOUT_TOKEN, others)
        self.assertFalse(CalculationEngine().evaluate(BLACKOUT_TOKEN, None).ok)

    def test_the_command_has_a_spoken_name(self) -> None:
        """Ctrl + Shift describes keys; this one must not be read out as "BLACKOUT"."""
        self.assertIn(BLACKOUT_TOKEN, SPOKEN_TOKEN_NAMES)
        self.assertNotEqual(spoken_token(BLACKOUT_TOKEN), BLACKOUT_TOKEN)

    def test_the_pc_has_no_shortcut_of_its_own(self) -> None:
        """Same command on both keyboards: Ctrl then Esc, like Ctrl + Ans."""
        self.assertNotIn(BLACKOUT_TOKEN, KeyboardAdapter.KEY_MAP.values())


class BlackoutShortcutWiringTest(unittest.TestCase):
    """4.3/4.4: Ctrl + AC toggles the screens and says so, on both fronts."""

    def test_ctrl_ac_from_the_keyboard_switches_off_then_back_on(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front, DisplayMode.HDMI) as app:
                ctrl_then_ac(app)
                self.assertTrue(app.blackout.active)
                self.assertEqual(spoken(app)[-1], video_blackout.blackout_speech())

                ctrl_then_ac(app)
                self.assertFalse(app.blackout.active)
                self.assertEqual(spoken(app)[-1], video_blackout.relit_speech(DisplayMode.HDMI))
                self.assertEqual(app.apply_video.calls, 2)

    def test_esc_stays_bound_as_the_ac_of_the_pc_keyboard(self) -> None:
        """Esc -> _handle_token("AC", None, None): exactly what ctrl_then_ac sends.

        A synthetic key event needs the window focused, which a headless test
        run cannot guarantee; the binding is checked instead.
        """
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                self.assertTrue(app.root.bind("<Escape>"))

    def test_the_on_screen_ac_button_with_ctrl_does_the_same(self) -> None:
        """The HDMI keypad passes the key's own secondary."""
        with front_app("hdmi") as app:
            app._handle_token("Ctrl", None, None)
            app._handle_token("AC", BLACKOUT_TOKEN, None)

            self.assertTrue(app.blackout.active)

    def test_a_failed_blackout_is_announced_and_leaves_the_screen_lit(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front, panel=None) as app:
                ctrl_then_ac(app)

                self.assertFalse(app.blackout.active)
                self.assertEqual(spoken(app)[-1], video_blackout.blackout_failed_speech())

    def test_a_front_started_on_its_own_reports_no_video_control(self) -> None:
        """Without the entry point nothing can switch X: say so, never crash."""
        for front in FRONTS:
            with self.subTest(front=front), front_app(front, applier=None) as app, \
                 self.assertLogs(video_blackout.logger, level="WARNING"):
                ctrl_then_ac(app)

                self.assertFalse(app.blackout.active)

    def test_a_shared_session_makes_the_new_front_born_dark(self) -> None:
        """RF-09 handover: the front receives the session the old one used."""
        session = video_blackout.VideoBlackout(active=True)
        for front in FRONTS:
            with self.subTest(front=front), front_app(front, blackout=session) as app:
                self.assertIs(app.blackout, session)


class AcRecoveryTest(unittest.TestCase):
    """Spec «Recuperação garantida pela tecla AC», on both fronts."""

    def test_ac_alone_relights_and_still_clears(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                ctrl_then_ac(app)
                app._handle_token("7", None, None)

                app._handle_token("AC", None, None)

                self.assertFalse(app.blackout.active)
                self.assertEqual(app.state.expression, "")
                self.assertIn(video_blackout.relit_speech(DisplayMode.LCD), spoken(app))

    def test_ac_with_the_screen_lit_does_not_touch_the_video(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                app._handle_token("7", None, None)

                app._handle_token("AC", None, None)

                self.assertEqual(app.apply_video.calls, 0)
                self.assertEqual(app.state.expression, "")


class BlackoutIsASecondaryFunctionTest(unittest.TestCase):
    """4.5"""

    def test_ctrl_ac_does_not_clear_the_expression(self) -> None:
        """The secondary replaces the primary: switching off is not "clear all"."""
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                app._handle_token("7", None, None)

                ctrl_then_ac(app)

                self.assertTrue(app.blackout.active)
                self.assertEqual(app.state.expression, "7")

    def test_ctrl_is_consumed_like_any_secondary_function(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                ctrl_then_ac(app)

                self.assertFalse(app.ctrl_active)
                self.assertEqual(app.ctrl_var.get(), "")

    def test_ctrl_shift_describes_ac_instead_of_switching_off(self) -> None:
        """Only the HDMI front has the "what does this key do?" mode."""
        with front_app("hdmi") as app:
            app._handle_token("Ctrl", None, None)
            app._handle_token("Shift", None, None)
            app.speech.reset_mock()

            app._handle_token("AC", None, None)

            self.assertFalse(app.blackout.active)
            self.assertEqual(app.apply_video.calls, 0)
            described = app.speech.say.call_args.args[0]
            self.assertIn(spoken_token("AC"), described)
            self.assertIn(spoken_token(BLACKOUT_TOKEN), described)


class CalculatorWorksInTheDarkTest(unittest.TestCase):
    """4.6: spec «Calculadora permanece operável com as telas apagadas»."""

    def snapshot(self, app) -> tuple:
        state = app.state
        return state.expression, state.ans, list(state.history), state.angle_mode

    def test_calculating_while_dark_and_state_survives_the_cycle(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), front_app(front) as app:
                ctrl_then_ac(app)
                self.assertTrue(app.blackout.active)

                for token in ("2", "+", "2", "="):
                    app._handle_token(token, None, None)
                self.assertIn("Resultado 4", spoken(app))
                self.assertEqual(app.state.history[-1].display, "4")

                app._handle_token("RAD/DEG", None, None)
                for token in ("+", "1"):
                    app._handle_token(token, None, None)
                before = self.snapshot(app)

                ctrl_then_ac(app)

                self.assertFalse(app.blackout.active)
                self.assertEqual(self.snapshot(app), before)
                self.assertEqual(app.state.angle_mode, "rad")
                self.assertEqual(app.expression_var.get(), app.state.expression)


if __name__ == "__main__":
    unittest.main()
