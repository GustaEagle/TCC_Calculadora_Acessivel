import contextlib
import io
import unittest
from unittest import mock

from software import app
from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    SimulatedHdmiPortReader,
)


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

    def test_hdmi_mode_starts_only_the_hdmi_front(self) -> None:
        with mock.patch("software.ui.hdmi.app.CalculatorApp") as hdmi, \
             mock.patch("software.ui.lcd.app.CalculatorApp") as lcd, \
             mock.patch("software.audio_only.AudioOnlyCalculator") as audio:
            app.run_mode(DisplayMode.HDMI)

        hdmi.return_value.run.assert_called_once()
        lcd.assert_not_called()
        audio.assert_not_called()

    def test_lcd_mode_starts_only_the_lcd_front(self) -> None:
        with mock.patch("software.ui.hdmi.app.CalculatorApp") as hdmi, \
             mock.patch("software.ui.lcd.app.CalculatorApp") as lcd, \
             mock.patch("software.audio_only.AudioOnlyCalculator") as audio:
            app.run_mode(DisplayMode.LCD)

        lcd.return_value.run.assert_called_once()
        hdmi.assert_not_called()
        audio.assert_not_called()

    def test_audio_only_mode_starts_no_visual_front(self) -> None:
        with mock.patch("software.ui.hdmi.app.CalculatorApp") as hdmi, \
             mock.patch("software.ui.lcd.app.CalculatorApp") as lcd, \
             mock.patch("software.audio_only.AudioOnlyCalculator") as audio:
            app.run_mode(DisplayMode.AUDIO_ONLY)

        audio.return_value.run.assert_called_once()
        hdmi.assert_not_called()
        lcd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
