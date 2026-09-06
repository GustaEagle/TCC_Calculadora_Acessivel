"""The front that takes over must look like the one that left (RF-09).

Regression from the hardware bring-up: after the monitor was plugged in and the
UI moved to it, the calculator came up completely unstyled.

ttkbootstrap keeps its Style in a class-level singleton bound to the Tcl
interpreter that created it. The handover destroys one root and builds another
in the same process, so the second window got the stale Style back, __init__
returned early without building anything, and the window fell back to Tk's
default theme (`vista` on Windows, `default` on the Pi).
"""

import unittest

from software.hw_platform.display import DisplayMode
from software.ui.shared.tk_session import reset_ttkbootstrap_globals

THEME = "darkly"


def load_front(mode: DisplayMode):
    front = "hdmi" if mode == DisplayMode.HDMI else "lcd"
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


def theme_of(app) -> str:
    return str(app.root.tk.call("ttk::style", "theme", "use"))


def primary_button_background(app) -> str:
    return str(app.root.tk.call("ttk::style", "lookup", "primary.TButton", "-background"))


class HandoverStylingTest(unittest.TestCase):
    """Each front must look the same whether or not another ran before it.

    The two fronts have deliberately different palettes, so they are never
    compared against each other - only each against itself, alone versus after
    a handover. That is exactly the difference the bug produced.
    """

    def styling_of(self, mode: DisplayMode) -> tuple[str, str]:
        app = load_front(mode)()
        try:
            return theme_of(app), primary_button_background(app)
        finally:
            app.root.destroy()

    def after_handover_from(self, previous: DisplayMode, mode: DisplayMode) -> tuple[str, str]:
        """Styling of `mode` when `previous` owned the process first."""
        reset_ttkbootstrap_globals()  # start from a clean process, as a boot would
        first = load_front(previous)()
        first.root.destroy()

        # No reset here on purpose: the front under test has to do it itself,
        # because run_mode() simply builds the next one.
        return self.styling_of(mode)

    def test_the_monitor_front_is_unchanged_by_the_lcd_running_first(self) -> None:
        """The reported bug: plug in the monitor, lose all styling."""
        reset_ttkbootstrap_globals()
        alone = self.styling_of(DisplayMode.HDMI)
        after = self.after_handover_from(DisplayMode.LCD, DisplayMode.HDMI)

        self.assertEqual(after[0], THEME, "o front do monitor subiu sem o tema")
        self.assertEqual(after, alone, "o front do monitor mudou de aparencia apos a troca")

    def test_the_lcd_front_is_unchanged_by_the_monitor_running_first(self) -> None:
        """The way back matters too: unplugging must not strip the LCD."""
        reset_ttkbootstrap_globals()
        alone = self.styling_of(DisplayMode.LCD)
        after = self.after_handover_from(DisplayMode.HDMI, DisplayMode.LCD)

        self.assertEqual(after[0], THEME, "o front do LCD voltou sem o tema")
        self.assertEqual(after, alone, "o front do LCD mudou de aparencia apos a troca")

    def test_a_real_themed_colour_is_applied_after_the_swap(self) -> None:
        """Not just the theme name: a system default would not be a hex colour."""
        after = self.after_handover_from(DisplayMode.LCD, DisplayMode.HDMI)

        self.assertTrue(
            after[1].startswith("#"),
            f"cor do tema nao aplicada apos a troca: {after[1]!r}",
        )

    def test_three_swaps_in_a_row_still_look_right(self) -> None:
        """RF-09 allows plugging and unplugging repeatedly."""
        reset_ttkbootstrap_globals()
        alone = self.styling_of(DisplayMode.HDMI)

        for _ in range(3):
            load_front(DisplayMode.LCD)().root.destroy()
            load_front(DisplayMode.HDMI)().root.destroy()

        self.assertEqual(self.styling_of(DisplayMode.HDMI), alone)


class ResetHelperTest(unittest.TestCase):
    def test_reset_is_safe_before_any_window_exists(self) -> None:
        from ttkbootstrap.style import Style

        Style.instance = None
        reset_ttkbootstrap_globals()  # must not raise
        self.assertIsNone(Style.instance)

    def test_reset_clears_a_stale_singleton(self) -> None:
        from ttkbootstrap.style import Style

        app = load_front(DisplayMode.LCD)()
        app.root.destroy()
        self.assertIsNotNone(Style.instance, "pre-condicao: o singleton ficou para tras")

        reset_ttkbootstrap_globals()
        self.assertIsNone(Style.instance)


if __name__ == "__main__":
    unittest.main()
