"""The monitor front must fill the panel it was pointed at (D6).

There is no window manager on the kiosk, so X places the window at (0,0) and
nothing maximises it. A fixed 1280x720 on a 1920x1080 monitor is not a smaller
calculator - it is a calculator in the top-left corner of a black screen.
"""

import unittest
from unittest import mock

from software.ui.hdmi.app import WINDOW_HEIGHT, WINDOW_WIDTH, screen_geometry


class ScreenGeometryTest(unittest.TestCase):
    def test_uses_the_real_resolution_of_the_active_display(self) -> None:
        self.assertEqual(screen_geometry(1920, 1080), "1920x1080")

    def test_the_lcd_resolution_is_honoured_too(self) -> None:
        self.assertEqual(screen_geometry(800, 480), "800x480")

    def test_an_unusable_screen_size_falls_back_to_the_reference(self) -> None:
        """A zero-sized window would hide the calculator completely."""
        for width, height in ((0, 0), (0, 1080), (1920, 0), (-1, -1)):
            self.assertEqual(
                screen_geometry(width, height), f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
            )


class FrontGeometryTest(unittest.TestCase):
    """7.1: the front asks Tk for the screen size, not for a constant."""

    def build_on_screen(self, width: int, height: int):
        """Instantiate the real front against a simulated screen size."""
        import ttkbootstrap as ttk

        with mock.patch.object(ttk.Window, "winfo_screenwidth", return_value=width), \
             mock.patch.object(ttk.Window, "winfo_screenheight", return_value=height), \
             mock.patch.object(ttk.Window, "geometry") as geometry:
            from software.ui.hdmi.app import CalculatorApp

            app = CalculatorApp()
            try:
                return geometry.call_args.args[0]
            finally:
                app.root.destroy()

    def test_a_1920x1080_monitor_gets_a_1920x1080_window(self) -> None:
        self.assertEqual(self.build_on_screen(1920, 1080), "1920x1080")

    def test_a_1366x768_monitor_gets_a_1366x768_window(self) -> None:
        """The resolution is read, not chosen from a list of known ones."""
        self.assertEqual(self.build_on_screen(1366, 768), "1366x768")

    def test_the_window_stays_non_resizable(self) -> None:
        import ttkbootstrap as ttk

        with mock.patch.object(ttk.Window, "winfo_screenwidth", return_value=1920), \
             mock.patch.object(ttk.Window, "winfo_screenheight", return_value=1080), \
             mock.patch.object(ttk.Window, "resizable") as resizable:
            from software.ui.hdmi.app import CalculatorApp

            app = CalculatorApp()
            try:
                self.assertEqual(resizable.call_args.args, (False, False))
            finally:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
