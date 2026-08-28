"""xrandr glue: point X at the panel that should show the UI (RF-09).

Detecting the change is not enough — X keeps driving whatever it configured at
startup, so a monitor plugged in later stays dark until an output is enabled.
"""

import unittest
from unittest import mock

from software.hw_platform import video_output


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
             mock.patch("subprocess.run") as run:
            self.assertTrue(
                video_output.activate("HDMI-2", disable=("HDMI-1", "HDMI-2"))
            )

        argv = run.call_args.args[0]
        self.assertEqual(argv[:5], ["xrandr", "--output", "HDMI-2", "--auto", "--primary"])
        self.assertEqual(argv[5:], ["--output", "HDMI-1", "--off"])

    def test_the_target_is_never_switched_off_by_its_own_call(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run") as run:
            video_output.activate("HDMI-1", disable=("HDMI-1", "HDMI-2"))

        argv = run.call_args.args[0]
        self.assertNotIn("--off", argv[:4])
        self.assertEqual(argv.count("--off"), 1)

    def test_a_failing_xrandr_is_reported_not_raised(self) -> None:
        """The UI must come up even if the outputs could not be reconfigured."""
        import subprocess

        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "xrandr")):
            self.assertFalse(video_output.activate("HDMI-2"))

    def test_a_hung_xrandr_does_not_hang_the_app(self) -> None:
        import subprocess

        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("xrandr", 10)):
            self.assertFalse(video_output.activate("HDMI-2"))

    def test_a_missing_xrandr_binary_is_not_fatal(self) -> None:
        with mock.patch.object(video_output, "available", return_value=True), \
             mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertFalse(video_output.activate("HDMI-2"))


if __name__ == "__main__":
    unittest.main()
