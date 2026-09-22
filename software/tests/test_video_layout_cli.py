"""The entry point's video-layout side: logging, --apply-video-layout, diagnostics.

The kiosk has no console to read - tty1 is covered by X - so the log file is the
only way to tell a working xrandr from a failed one, and the layout has to be
applied before any window exists or the extended desktop shows up on both panels.
"""

import contextlib
import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from software import app
from software.hw_platform.display import DisplayMode


@contextlib.contextmanager
def isolated_logging():
    """Restore the root logger, since configure_logging() takes it over."""
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        yield
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()
        root.handlers.extend(saved[0])
        root.setLevel(saved[1])


class LoggingConfigTest(unittest.TestCase):
    """3.1: the bring-up needs to see what xrandr did without unmounting the kiosk."""

    def test_messages_land_in_the_file_named_by_the_env_var(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calculadora.log"
            with isolated_logging(), \
                 mock.patch.dict("os.environ", {app.LOG_FILE_ENV: str(path)}):
                app.configure_logging()
                logging.getLogger("software.teste").warning("WRN-012 mensagem de prova")

            self.assertIn("WRN-012 mensagem de prova", path.read_text(encoding="utf-8"))

    def test_an_unwritable_path_falls_back_instead_of_failing_the_boot(self) -> None:
        """A log that cannot be opened must never be the reason the Pi shows nothing."""
        unwritable = str(Path(tempfile.gettempdir()) / "sem-tal-pasta" / "x.log")
        stderr = io.StringIO()
        with isolated_logging(), \
             mock.patch.dict("os.environ", {app.LOG_FILE_ENV: unwritable}):
            app.configure_logging()  # must not raise
            # The fallback handler binds stderr at construction, so redirecting
            # afterwards would miss it; point the handler at the buffer instead.
            for handler in logging.getLogger().handlers:
                handler.stream = stderr
            logging.getLogger("software.teste").warning("ainda registra")

            self.assertTrue(logging.getLogger().handlers)

        self.assertIn("ainda registra", stderr.getvalue())

    def test_the_default_path_is_in_the_users_home(self) -> None:
        self.assertEqual(app.default_log_path().name, "calculadora.log")
        self.assertEqual(app.default_log_path().parent, Path.home())


class ApplyVideoLayoutTest(unittest.TestCase):
    """4.1/4.2: apply the layout and exit, without ever building a front."""

    def run_main(self, argv: list[str]) -> tuple[int, mock.Mock]:
        loaded = set(sys.modules)
        with isolated_logging(), \
             mock.patch.object(app, "configure_logging"), \
             mock.patch.object(app, "run_mode") as run_mode, \
             mock.patch("software.hw_platform.video_output.activate") as activate, \
             mock.patch("software.hw_platform.video_output.read_outputs", return_value={}):
            code = app.main(argv)

        run_mode.assert_not_called()
        # Neither front may be pulled in: this path runs before X has a layout,
        # and importing Tk here would be the window we are trying to avoid.
        for module in set(sys.modules) - loaded:
            self.assertNotIn("software.ui.", module)
        return code, activate

    def test_the_layout_is_applied_and_no_front_is_started(self) -> None:
        code, activate = self.run_main(["--apply-video-layout", "--force-mode", "hdmi"])

        self.assertEqual(code, 0)
        activate.assert_called_once()

    def test_audio_only_reconfigures_nothing(self) -> None:
        """No usable video means there is no output to point anywhere."""
        code, activate = self.run_main(["--apply-video-layout", "--force-mode", "audio"])

        self.assertEqual(code, 0)
        activate.assert_not_called()

    def test_the_mode_is_passed_to_activate_for_the_log(self) -> None:
        _code, activate = self.run_main(["--apply-video-layout", "--force-mode", "lcd"])

        self.assertEqual(activate.call_args.kwargs["mode"], DisplayMode.LCD.value)

    def test_the_target_is_the_monitor_in_hdmi_mode(self) -> None:
        _code, activate = self.run_main(["--apply-video-layout", "--force-mode", "hdmi"])

        lcd, monitor = "HDMI-1", "HDMI-2"
        self.assertEqual(activate.call_args.args[0], monitor)
        self.assertEqual(set(activate.call_args.kwargs["disable"]), {lcd, monitor})


class FlagCombinationTest(unittest.TestCase):
    """4.3: the flag has to coexist with the two that were already there."""

    def test_the_parser_accepts_the_flag_with_force_mode(self) -> None:
        args = app.build_parser().parse_args(["--apply-video-layout", "--force-mode", "hdmi"])
        self.assertTrue(args.apply_video_layout)
        self.assertEqual(args.force_mode, "hdmi")

    def test_the_flag_defaults_to_off(self) -> None:
        self.assertFalse(app.build_parser().parse_args([]).apply_video_layout)

    def test_list_outputs_reports_and_exits_without_touching_the_screen(self) -> None:
        """Diagnostics must stay safe to run on a machine showing the UI."""
        with isolated_logging(), \
             mock.patch.object(app, "configure_logging"), \
             mock.patch.object(app, "point_x_at") as point_x, \
             mock.patch.object(app, "run_mode") as run_mode, \
             mock.patch("software.hw_platform.video_output.read_outputs", return_value={}), \
             contextlib.redirect_stdout(io.StringIO()):
            code = app.main(["--list-outputs", "--apply-video-layout"])

        self.assertEqual(code, 0)
        point_x.assert_not_called()
        run_mode.assert_not_called()

    def test_simulate_monitor_drives_the_layout_without_hardware(self) -> None:
        with isolated_logging(), \
             mock.patch.object(app, "configure_logging"), \
             mock.patch("software.hw_platform.video_output.activate") as activate, \
             mock.patch("software.hw_platform.video_output.read_outputs", return_value={}):
            app.main(["--apply-video-layout", "--simulate-monitor"])

        self.assertEqual(activate.call_args.kwargs["mode"], DisplayMode.HDMI.value)


class PrintOutputsTest(unittest.TestCase):
    """5.1/5.2: one command answering both halves of the bring-up checklist."""

    def capture(self, connectors: dict[str, str], outputs: dict[str, bool]) -> str:
        reader = mock.Mock()
        reader.list_connectors.return_value = connectors
        reader.drm_path = "/sys/class/drm"
        reader.lcd_connector = "HDMI-A-1"
        reader.monitor_connector = "HDMI-A-2"
        reader.available.return_value = bool(connectors)

        buffer = io.StringIO()
        with mock.patch.object(app, "SysfsHdmiPortReader", return_value=reader), \
             mock.patch("software.hw_platform.video_output.read_outputs", return_value=outputs), \
             mock.patch.dict("os.environ", {}, clear=True), \
             contextlib.redirect_stdout(buffer):
            app.print_outputs()
        return buffer.getvalue()

    def test_prints_drm_outputs_x_outputs_and_the_mapping(self) -> None:
        printed = self.capture(
            {"HDMI-A-1": "connected", "HDMI-A-2": "connected"},
            {"HDMI-1": True, "HDMI-2": False},
        )

        self.assertIn("Conectores DRM", printed)
        self.assertIn("HDMI-A-1: connected", printed)
        self.assertIn("Saidas do servidor X", printed)
        self.assertIn("HDMI-1: ativa", printed)
        self.assertIn("HDMI-2: inativa", printed)
        self.assertIn("Mapeamento em uso", printed)
        self.assertIn("HDMI-A-2 -> HDMI-2", printed)

    def test_a_machine_with_neither_reports_both_absences(self) -> None:
        """A developer PC: no DRM connectors, no X server, and still exit 0."""
        printed = self.capture({}, {})

        self.assertIn("nenhum encontrado", printed)
        self.assertIn("nenhuma (sem DISPLAY", printed)

    def test_the_diagnostic_exits_zero_on_a_machine_without_video(self) -> None:
        with isolated_logging(), \
             mock.patch.object(app, "configure_logging"), \
             mock.patch.object(app, "print_outputs"):
            self.assertEqual(app.main(["--list-outputs"]), 0)


if __name__ == "__main__":
    unittest.main()
