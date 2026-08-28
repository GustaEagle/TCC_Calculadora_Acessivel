import contextlib
import io
import unittest
from unittest import mock

from software import app
from software.core import CalculatorState
from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    SimulatedHdmiPortReader,
)


class FakeSpeech:
    def say(self, text: str) -> None:
        pass

    def interrupt_and_say(self, text: str) -> None:
        pass

    def stop(self) -> None:
        pass


@contextlib.contextmanager
def fake_fronts(hands_over_to=()):
    """Patch the three fronts; `hands_over_to` is what run() returns in turn.

    A front returning None means "the user quit", which is what ends the loop.
    """
    # One iterator SHARED by both fronts: the handovers are a sequence of runs,
    # not a sequence per front (a list per mock would replay from the start and
    # loop between the two forever).
    handovers = iter(list(hands_over_to) + [None])
    with mock.patch("software.ui.hdmi.app.CalculatorApp") as hdmi, \
         mock.patch("software.ui.lcd.app.CalculatorApp") as lcd, \
         mock.patch("software.audio_only.AudioOnlyCalculator") as audio, \
         mock.patch.object(app, "point_x_at") as point_x:
        hdmi.return_value.run.side_effect = lambda: next(handovers)
        lcd.return_value.run.side_effect = lambda: next(handovers)
        audio.return_value.run.return_value = None
        yield hdmi, lcd, audio, point_x


class ResolveModeTest(unittest.TestCase):
    def test_uses_selector_when_no_mode_is_forced(self) -> None:
        selector = DisplaySelector(SimulatedHdmiPortReader(monitor_present=True))
        self.assertEqual(app.resolve_mode(None, selector), DisplayMode.HDMI)

    def test_force_mode_overrides_detection(self) -> None:
        selector = DisplaySelector(SimulatedHdmiPortReader(monitor_present=True))
        self.assertEqual(app.resolve_mode("lcd", selector), DisplayMode.LCD)
        self.assertEqual(app.resolve_mode("audio", selector), DisplayMode.AUDIO_ONLY)

    def test_every_force_mode_choice_maps_to_a_display_mode(self) -> None:
        for choice in app._FORCED_MODES:
            self.assertIsInstance(app.resolve_mode(choice), DisplayMode)

    def test_parser_accepts_exactly_the_supported_force_modes(self) -> None:
        parser = app.build_parser()
        for choice in app._FORCED_MODES:
            self.assertEqual(parser.parse_args(["--force-mode", choice]).force_mode, choice)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--force-mode", "braille"])


class RunModeDispatchTest(unittest.TestCase):
    """Exactly one front must start per run (never both, never none)."""

    def run_mode(self, mode: DisplayMode) -> None:
        app.run_mode(mode, CalculatorState(), FakeSpeech())

    def test_hdmi_mode_starts_only_the_hdmi_front(self) -> None:
        with fake_fronts() as (hdmi, lcd, audio, _point_x):
            self.run_mode(DisplayMode.HDMI)

        hdmi.return_value.run.assert_called_once()
        lcd.assert_not_called()
        audio.assert_not_called()

    def test_lcd_mode_starts_only_the_lcd_front(self) -> None:
        with fake_fronts() as (hdmi, lcd, audio, _point_x):
            self.run_mode(DisplayMode.LCD)

        lcd.return_value.run.assert_called_once()
        hdmi.assert_not_called()
        audio.assert_not_called()

    def test_audio_only_mode_starts_no_visual_front(self) -> None:
        with fake_fronts() as (hdmi, lcd, audio, _point_x):
            self.run_mode(DisplayMode.AUDIO_ONLY)

        audio.return_value.run.assert_called_once()
        hdmi.assert_not_called()
        lcd.assert_not_called()


class FrontHandoverTest(unittest.TestCase):
    """RF-09: the swap happens in-process, keeping the calculation alive."""

    def test_lcd_hands_over_to_the_hdmi_front(self) -> None:
        with fake_fronts([DisplayMode.HDMI]) as (hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        lcd.return_value.run.assert_called_once()
        hdmi.return_value.run.assert_called_once()

    def test_the_same_state_is_handed_to_the_next_front(self) -> None:
        """The whole point: the expression and history survive the swap."""
        state = CalculatorState()
        state.press("7")

        with fake_fronts([DisplayMode.HDMI]) as (hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.LCD, state, FakeSpeech())

        self.assertIs(lcd.call_args.args[0], state)
        self.assertIs(hdmi.call_args.args[0], state)
        self.assertEqual(state.expression, "7")

    def test_the_speech_service_is_not_rebuilt_between_fronts(self) -> None:
        speech = FakeSpeech()
        with fake_fronts([DisplayMode.HDMI]) as (hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), speech)

        self.assertIs(lcd.call_args.args[1], speech)
        self.assertIs(hdmi.call_args.args[1], speech)

    def test_x_is_pointed_at_each_panel_as_it_takes_over(self) -> None:
        with fake_fronts([DisplayMode.HDMI]) as (_hdmi, _lcd, _audio, point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        self.assertEqual(
            [call.args[0] for call in point_x.call_args_list],
            [DisplayMode.LCD, DisplayMode.HDMI],
        )

    def test_losing_the_monitor_hands_back_to_the_lcd(self) -> None:
        with fake_fronts([DisplayMode.LCD]) as (hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.HDMI, CalculatorState(), FakeSpeech())

        hdmi.return_value.run.assert_called_once()
        lcd.return_value.run.assert_called_once()

    def test_a_front_returning_none_ends_the_loop(self) -> None:
        with fake_fronts() as (_hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        lcd.return_value.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
