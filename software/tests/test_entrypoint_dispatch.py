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
from software.ui.shared.video_blackout import VideoBlackout


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


@contextlib.contextmanager
def fake_x(outputs=("HDMI-1", "HDMI-2")):
    """The real point_x_at, with only the xrandr calls replaced."""
    with mock.patch.object(app, "resolve_output_names", return_value=outputs), \
         mock.patch("software.hw_platform.video_output.activate", return_value=True) as activate, \
         mock.patch("software.hw_platform.video_output.all_off", return_value=True) as all_off:
        yield activate, all_off


class BlackoutSessionTest(unittest.TestCase):
    """video-blackout 3.1: one session per run, shared by X and every front."""

    def test_the_same_blackout_reaches_x_and_every_front(self) -> None:
        with fake_fronts([DisplayMode.HDMI]) as (hdmi, lcd, _audio, point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        blackout = lcd.call_args.kwargs["blackout"]
        self.assertIsInstance(blackout, VideoBlackout)
        self.assertIs(hdmi.call_args.kwargs["blackout"], blackout)
        for call in point_x.call_args_list:
            self.assertIs(call.args[1], blackout)

    def test_every_run_starts_lit(self) -> None:
        """Never persisted: a restart after a blackout comes up with a picture."""
        with fake_fronts() as (_hdmi, lcd, _audio, _point_x):
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        self.assertFalse(lcd.call_args.kwargs["blackout"].active)


class PointXAtBlackoutTest(unittest.TestCase):
    """video-blackout 3.2: one point applies video, lit or dark."""

    def test_lit_session_keeps_the_exclusive_layout(self) -> None:
        with fake_x() as (activate, all_off):
            self.assertTrue(app.point_x_at(DisplayMode.HDMI, VideoBlackout(active=False)))

        activate.assert_called_once()
        self.assertEqual(activate.call_args.args[0], "HDMI-2")
        all_off.assert_not_called()

    def test_dark_session_switches_every_panel_off(self) -> None:
        with fake_x() as (activate, all_off):
            self.assertTrue(app.point_x_at(DisplayMode.LCD, VideoBlackout(active=True)))

        all_off.assert_called_once()
        self.assertEqual(all_off.call_args.args[0], ("HDMI-1", "HDMI-2"))
        activate.assert_not_called()

    def test_without_a_session_nothing_changes(self) -> None:
        """--apply-video-layout runs before any front: always lit."""
        with fake_x() as (activate, all_off):
            app.point_x_at(DisplayMode.LCD)

        activate.assert_called_once()
        all_off.assert_not_called()

    def test_audio_only_touches_no_output_even_in_a_blackout(self) -> None:
        with fake_x() as (activate, all_off):
            self.assertFalse(app.point_x_at(DisplayMode.AUDIO_ONLY, VideoBlackout(active=True)))

        activate.assert_not_called()
        all_off.assert_not_called()


class RelightPriorityTest(unittest.TestCase):
    """video-blackout 3.3: relighting re-runs §7.2 instead of remembering a panel."""

    def test_a_monitor_plugged_in_during_the_blackout_is_the_one_that_relights(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=False)
        blackout = VideoBlackout()
        apply = app.make_video_applier(DisplayMode.LCD, blackout, DisplaySelector(reader))

        with fake_x() as (activate, all_off):
            blackout.active = True
            self.assertIsNotNone(apply())
            all_off.assert_called_once()

            reader.monitor_present = True
            blackout.active = False
            self.assertEqual(apply(), DisplayMode.HDMI)

        self.assertEqual(activate.call_args.args[0], "HDMI-2")

    def test_a_monitor_removed_during_the_blackout_relights_the_lcd(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=True)
        blackout = VideoBlackout(active=True)
        apply = app.make_video_applier(DisplayMode.HDMI, blackout, DisplaySelector(reader))

        with fake_x() as (activate, _all_off):
            reader.monitor_present = False
            blackout.active = False
            self.assertEqual(apply(), DisplayMode.LCD)

        self.assertEqual(activate.call_args.args[0], "HDMI-1")

    def test_a_forced_mode_relights_its_own_panel(self) -> None:
        """No selector (--force-mode): detection must not override the demo."""
        blackout = VideoBlackout()
        apply = app.make_video_applier(DisplayMode.LCD, blackout, None)

        with fake_x() as (activate, _all_off):
            self.assertEqual(apply(), DisplayMode.LCD)

        self.assertEqual(activate.call_args.args[0], "HDMI-1")

    def test_an_unconfirmed_change_reports_no_panel(self) -> None:
        blackout = VideoBlackout(active=True)
        apply = app.make_video_applier(DisplayMode.LCD, blackout, None)

        with fake_x() as (_activate, all_off):
            all_off.return_value = False
            self.assertIsNone(apply())

    def test_main_passes_a_selector_only_when_the_mode_is_detected(self) -> None:
        with mock.patch.object(app, "configure_logging"), \
             mock.patch.object(app, "run_mode", return_value=0) as run_mode:
            app.main(["--force-mode", "lcd"])
            self.assertIsNone(run_mode.call_args.kwargs["selector"])

            app.main(["--simulate-monitor"])
            self.assertIsInstance(run_mode.call_args.kwargs["selector"], DisplaySelector)


class BlackoutSurvivesHandoverTest(unittest.TestCase):
    """video-blackout 3.4: a hotplug during the blackout does not relight anything."""

    def test_the_front_taking_over_is_born_dark(self) -> None:
        def lcd_run():
            # The user switches the screens off, then the monitor arrives.
            lcd.call_args.kwargs["blackout"].active = True
            return DisplayMode.HDMI

        with fake_x() as (activate, all_off), \
             mock.patch("software.ui.hdmi.app.CalculatorApp") as hdmi, \
             mock.patch("software.ui.lcd.app.CalculatorApp") as lcd:
            lcd.return_value.run.side_effect = lcd_run
            hdmi.return_value.run.return_value = None
            app.run_mode(DisplayMode.LCD, CalculatorState(), FakeSpeech())

        activate.assert_called_once()          # boot: the LCD lit
        self.assertEqual(activate.call_args.kwargs["mode"], DisplayMode.LCD.value)
        all_off.assert_called_once()           # handover: the monitor stays dark
        self.assertEqual(all_off.call_args.kwargs["mode"], DisplayMode.HDMI.value)
        self.assertTrue(hdmi.call_args.kwargs["blackout"].active)


class AudioOnlyIgnoresBlackoutTest(unittest.TestCase):
    """video-blackout 3.5: no screen, nothing to switch off."""

    def test_audio_front_is_built_without_the_blackout(self) -> None:
        state, speech = CalculatorState(), FakeSpeech()
        with fake_fronts() as (_hdmi, _lcd, audio, _point_x):
            app.run_mode(DisplayMode.AUDIO_ONLY, state, speech)

        audio.assert_called_once_with(state, speech)


if __name__ == "__main__":
    unittest.main()
