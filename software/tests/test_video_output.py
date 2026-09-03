"""xrandr glue: point X at the panel that should show the UI (RF-09).

Detecting the change is not enough - X keeps driving whatever it configured at
startup, so a monitor plugged in later stays dark until an output is enabled.
And enabling it is not enough either: the exit code says the command was
accepted, not that the panel actually changed, which is how both screens stayed
lit while the code reported success.
"""

import subprocess
import unittest
from unittest import mock

from software.hw_platform import video_output

# Real `xrandr --query` output from a Pi driving the LCD only: the monitor is
# plugged in but has no CRTC, which is the state the exclusivity has to produce.
QUERY_LCD_ONLY = """Screen 0: minimum 320 x 200, current 800 x 480, maximum 16384 x 16384
HDMI-1 connected primary 800x480+0+0 (normal left inverted right x axis y axis) 154mm x 86mm
   800x480       59.90*+
HDMI-2 connected (normal left inverted right x axis y axis) 598mm x 336mm
   1920x1080     60.00 +  50.00    59.94
"""

# The bug: X autoconfigured both panels side by side (an extended desktop).
QUERY_EXTENDED = """Screen 0: minimum 320 x 200, current 2720 x 1080, maximum 16384 x 16384
HDMI-1 connected primary 800x480+0+0 (normal left inverted right x axis y axis) 154mm x 86mm
   800x480       59.90*+
HDMI-2 connected 1920x1080+800+0 (normal left inverted right x axis y axis) 598mm x 336mm
   1920x1080     60.00*+  50.00
"""

QUERY_MONITOR_ONLY = """Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 16384 x 16384
HDMI-1 connected (normal left inverted right x axis y axis) 154mm x 86mm
   800x480       59.90 +
HDMI-2 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 598mm x 336mm
   1920x1080     60.00*+  50.00
"""


def fake_query(stdout: str):
    """A subprocess.run stand-in that answers `xrandr --query` with `stdout`."""
    return mock.Mock(returncode=0, stdout=stdout, stderr="")


class ReadOutputsTest(unittest.TestCase):
    """1.1/1.2: read the outputs X really has, and never raise doing it."""

    def read(self, stdout: str) -> dict[str, bool]:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", return_value=fake_query(stdout)):
            return video_output.read_outputs()

    def test_parses_names_and_active_state(self) -> None:
        """Active means "has a CRTC", not merely "has a cable in"."""
        self.assertEqual(self.read(QUERY_LCD_ONLY), {"HDMI-1": True, "HDMI-2": False})

    def test_an_extended_desktop_shows_both_outputs_active(self) -> None:
        self.assertEqual(self.read(QUERY_EXTENDED), {"HDMI-1": True, "HDMI-2": True})

    def test_disconnected_outputs_are_listed_as_inactive(self) -> None:
        stdout = (
            "Screen 0: minimum 320 x 200, current 800 x 480, maximum 16384 x 16384\n"
            "HDMI-1 connected primary 800x480+0+0 (normal left inverted) 154mm x 86mm\n"
            "HDMI-2 disconnected (normal left inverted right x axis y axis)\n"
        )
        self.assertEqual(self.read(stdout), {"HDMI-1": True, "HDMI-2": False})

    def test_no_x_server_reads_as_unknown(self) -> None:
        with mock.patch.object(video_output, "available", return_value=False), \
             mock.patch("subprocess.run") as run:
            self.assertEqual(video_output.read_outputs(), {})

        run.assert_not_called()

    def test_a_missing_xrandr_binary_reads_as_unknown(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(video_output.read_outputs(), {})

    def test_a_hung_xrandr_reads_as_unknown(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("xrandr", 10)):
            self.assertEqual(video_output.read_outputs(), {})

    def test_a_failing_xrandr_reads_as_unknown(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "xrandr")):
            self.assertEqual(video_output.read_outputs(), {})

    def test_unexpected_output_format_reads_as_unknown(self) -> None:
        """A future xrandr that prints something else must not crash the boot."""
        self.assertEqual(self.read("uma saida completamente diferente\n"), {})


class NameMappingTest(unittest.TestCase):
    def test_drm_names_become_xrandr_names(self) -> None:
        """sysfs says HDMI-A-1; the X modesetting driver says HDMI-1."""
        self.assertEqual(video_output.drm_to_xrandr("HDMI-A-1"), "HDMI-1")
        self.assertEqual(video_output.drm_to_xrandr("HDMI-A-2"), "HDMI-2")

    def test_an_env_var_overrides_the_convention(self) -> None:
        """Bring-up may find other names on this kernel/driver pair."""
        with mock.patch.dict("os.environ", {"CALC_LCD_XRANDR_OUTPUT": "HDMI1"}):
            self.assertEqual(
                video_output.output_name("HDMI-A-1", video_output.LCD_OUTPUT_ENV),
                "HDMI1",
            )

    def test_without_the_env_var_the_connector_is_converted(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                video_output.output_name("HDMI-A-2", video_output.MONITOR_OUTPUT_ENV),
                "HDMI-2",
            )

    def test_the_env_var_wins_over_an_output_present_in_x(self) -> None:
        """Highest precedence, so bring-up can force a name without a rebuild."""
        with mock.patch.dict("os.environ", {"CALC_MONITOR_XRANDR_OUTPUT": "DSI-1"}):
            self.assertEqual(
                video_output.output_name(
                    "HDMI-A-2", video_output.MONITOR_OUTPUT_ENV, {"HDMI-2": False}
                ),
                "DSI-1",
            )

    def test_a_name_present_in_x_wins_over_the_convention(self) -> None:
        """The whole bug: this kernel spells it HDMI2, the convention guessed HDMI-2."""
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                video_output.output_name(
                    "HDMI-A-2", video_output.MONITOR_OUTPUT_ENV, {"HDMI1": True, "HDMI2": False}
                ),
                "HDMI2",
            )

    def test_matching_ignores_hyphens_and_case(self) -> None:
        for spelling in ("HDMI-A-2", "HDMI-2", "HDMI2", "hdmi-2"):
            with mock.patch.dict("os.environ", {}, clear=True):
                self.assertEqual(
                    video_output.output_name(
                        "HDMI-A-2", video_output.MONITOR_OUTPUT_ENV, {spelling: False}
                    ),
                    spelling,
                )

    def test_falls_back_to_the_convention_when_x_knows_no_such_port(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                video_output.output_name(
                    "HDMI-A-2", video_output.MONITOR_OUTPUT_ENV, {"DP-1": True}
                ),
                "HDMI-2",
            )


class LayoutMatchesTest(unittest.TestCase):
    """2.1: comparing the state read from X against the layout we want."""

    def test_target_alone_active_is_a_match(self) -> None:
        self.assertIs(
            video_output.layout_matches("HDMI-2", ("HDMI-1",), {"HDMI-1": False, "HDMI-2": True}),
            True,
        )

    def test_an_extended_desktop_is_not_a_match(self) -> None:
        self.assertIs(
            video_output.layout_matches("HDMI-2", ("HDMI-1",), {"HDMI-1": True, "HDMI-2": True}),
            False,
        )

    def test_the_wrong_panel_being_the_active_one_is_not_a_match(self) -> None:
        self.assertIs(
            video_output.layout_matches("HDMI-2", ("HDMI-1",), {"HDMI-1": True, "HDMI-2": False}),
            False,
        )

    def test_an_unreadable_state_is_neither_a_match_nor_a_mismatch(self) -> None:
        """None, not False: not knowing is not the same as knowing it is wrong."""
        self.assertIsNone(video_output.layout_matches("HDMI-2", ("HDMI-1",), {}))

    def test_a_target_x_does_not_know_is_unreadable(self) -> None:
        self.assertIsNone(
            video_output.layout_matches("HDMI-9", ("HDMI-1",), {"HDMI-1": True})
        )


class ActivateTest(unittest.TestCase):
    def test_does_nothing_without_an_x_server(self) -> None:
        """A developer machine has no DISPLAY and needs none of this."""
        with mock.patch.object(video_output, "available", return_value=False), \
             mock.patch("subprocess.run") as run:
            self.assertFalse(video_output.activate("HDMI-2"))

        run.assert_not_called()

    def test_enables_the_target_and_disables_the_other_in_one_call(self) -> None:
        """One xrandr call, so the server reconfigures once instead of blanking."""
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(
                 video_output, "layout_matches", side_effect=[False, True]
             ), \
             mock.patch("subprocess.run") as run:
            self.assertTrue(
                video_output.activate("HDMI-2", disable=("HDMI-1", "HDMI-2"))
            )

        argv = run.call_args.args[0]
        self.assertEqual(argv[:5], ["xrandr", "--output", "HDMI-2", "--auto", "--primary"])
        self.assertEqual(argv[5:], ["--output", "HDMI-1", "--off"])

    def test_the_target_is_never_switched_off_by_its_own_call(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "layout_matches", side_effect=[False, True]), \
             mock.patch("subprocess.run") as run:
            video_output.activate("HDMI-1", disable=("HDMI-1", "HDMI-2"))

        argv = run.call_args.args[0]
        self.assertNotIn("--off", argv[:4])
        self.assertEqual(argv.count("--off"), 1)

    def test_a_failing_xrandr_is_reported_not_raised(self) -> None:
        """The UI must come up even if the outputs could not be reconfigured."""
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "layout_matches", return_value=False), \
             mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "xrandr")):
            self.assertFalse(video_output.activate("HDMI-2"))

    def test_a_hung_xrandr_does_not_hang_the_app(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "layout_matches", return_value=False), \
             mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("xrandr", 10)):
            self.assertFalse(video_output.activate("HDMI-2"))

    def test_a_missing_xrandr_binary_is_not_fatal(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "layout_matches", return_value=False), \
             mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertFalse(video_output.activate("HDMI-2"))


class ActivateIdempotenceTest(unittest.TestCase):
    """2.2: the boot-time call and the per-front call must not re-flash the screen."""

    def test_a_correct_layout_skips_xrandr_entirely(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               return_value={"HDMI-1": False, "HDMI-2": True}), \
             mock.patch("subprocess.run") as run:
            self.assertTrue(video_output.activate("HDMI-2", disable=("HDMI-1",)))

        run.assert_not_called()

    def test_an_extended_desktop_is_reconfigured(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               side_effect=[{"HDMI-1": True, "HDMI-2": True},
                                            {"HDMI-1": False, "HDMI-2": True}]), \
             mock.patch("subprocess.run") as run:
            self.assertTrue(video_output.activate("HDMI-2", disable=("HDMI-1",)))

        run.assert_called_once()


class ActivateVerificationTest(unittest.TestCase):
    """2.3/2.4: exit code 0 is not proof that the CRTC changed."""

    def test_a_confirmed_layout_is_reported_as_success(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               side_effect=[{"HDMI-1": True, "HDMI-2": True},
                                            {"HDMI-1": False, "HDMI-2": True}]), \
             mock.patch("subprocess.run"):
            self.assertTrue(video_output.activate("HDMI-2", disable=("HDMI-1",)))

    def test_xrandr_succeeding_while_the_lcd_stays_on_is_a_failure(self) -> None:
        """Exactly the observed bug: command accepted, both panels still lit."""
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               side_effect=[{"HDMI-1": True, "HDMI-2": True},
                                            {"HDMI-1": True, "HDMI-2": True}]), \
             mock.patch("subprocess.run") as run:
            self.assertFalse(video_output.activate("HDMI-2", disable=("HDMI-1",)))

        run.assert_called_once()

    def test_an_unverifiable_state_is_reported_but_does_not_raise(self) -> None:
        """The front still has to start; only the return value says "unproven"."""
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs", side_effect=[{}, {}]), \
             mock.patch("subprocess.run"):
            self.assertFalse(video_output.activate("HDMI-2", disable=("HDMI-1",)))


class LayoutLoggingTest(unittest.TestCase):
    """3.2: a bring-up with no console must still be able to see what happened."""

    def test_a_failure_logs_wrn_012_with_the_mode_and_the_names(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               side_effect=[{"HDMI-1": True, "HDMI-2": True},
                                            {"HDMI-1": True, "HDMI-2": True}]), \
             mock.patch("subprocess.run"), \
             self.assertLogs(video_output.logger, level="WARNING") as logs:
            video_output.activate("HDMI-2", disable=("HDMI-1",), mode="hdmi")

        recorded = "\n".join(logs.output)
        self.assertIn("WRN-012", recorded)
        self.assertIn("hdmi", recorded)
        self.assertIn("HDMI-2", recorded)
        self.assertIn("HDMI-1", recorded)

    def test_a_success_is_logged_with_the_mode_and_the_names(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch.object(video_output, "read_outputs",
                               side_effect=[{"HDMI-1": True, "HDMI-2": True},
                                            {"HDMI-1": False, "HDMI-2": True}]), \
             mock.patch("subprocess.run"), \
             self.assertLogs(video_output.logger, level="INFO") as logs:
            video_output.activate("HDMI-2", disable=("HDMI-1",), mode="hdmi")

        recorded = "\n".join(logs.output)
        self.assertNotIn("WRN-012", recorded)
        self.assertIn("hdmi", recorded)
        self.assertIn("HDMI-2", recorded)


if __name__ == "__main__":
    unittest.main()
