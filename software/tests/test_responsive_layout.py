import unittest

from software.ui.shared.responsive import (
    FONT_SPECS,
    MAX_SCALE,
    MIN_SCALE,
    font_sizes,
    responsive_scale,
    visible_chars,
)

# Resolutions the monitor front is expected to handle, smallest first.
_RESOLUTIONS = [(800, 480), (1280, 720), (1366, 768), (1920, 1080), (3840, 2160)]


class ResponsiveScaleTest(unittest.TestCase):
    """The HDMI front must adapt to the resolution instead of assuming one."""

    def test_scale_grows_with_the_screen(self) -> None:
        scales = [responsive_scale(w, h) for w, h in _RESOLUTIONS]
        self.assertEqual(scales, sorted(scales), f"escala nao acompanha a resolucao: {scales}")
        self.assertLess(scales[0], scales[-1], "800x480 e 4K produziram a mesma escala")

    def test_reference_resolution_scales_to_one(self) -> None:
        self.assertAlmostEqual(responsive_scale(1280, 720), 1.0)

    def test_scale_is_clamped_at_both_ends(self) -> None:
        self.assertEqual(responsive_scale(1, 1), MIN_SCALE)
        self.assertEqual(responsive_scale(100_000, 100_000), MAX_SCALE)

    def test_short_wide_window_does_not_overflow_vertically(self) -> None:
        """A wide-but-short window must scale by the limiting axis (height)."""
        self.assertLess(responsive_scale(3840, 600), responsive_scale(3840, 2160))


class FontSizesTest(unittest.TestCase):
    def test_fonts_differ_between_resolutions(self) -> None:
        small = font_sizes(responsive_scale(1366, 768))
        large = font_sizes(responsive_scale(1920, 1080))
        self.assertNotEqual(small, large)
        for role in FONT_SPECS:
            self.assertLess(small[role], large[role], f"fonte '{role}' nao acompanhou a tela")

    def test_fonts_never_fall_below_their_legibility_floor(self) -> None:
        tiny = font_sizes(MIN_SCALE)
        for role, (_base, floor) in FONT_SPECS.items():
            self.assertGreaterEqual(tiny[role], floor, f"fonte '{role}' ficou ilegivel")

    def test_result_stays_the_most_prominent_text(self) -> None:
        for width, height in _RESOLUTIONS:
            sizes = font_sizes(responsive_scale(width, height))
            self.assertGreater(
                sizes["result"], sizes["expression"],
                f"resultado deixou de ser o texto dominante em {width}x{height}",
            )
            self.assertGreater(sizes["expression"], sizes["button"])


class VisibleCharsTest(unittest.TestCase):
    def test_capacity_stays_stable_while_the_font_still_scales(self) -> None:
        """Below the font-scale cap the text grows with the window, so capacity
        holds steady instead of collapsing on a smaller monitor."""
        unclamped = [(w, h) for w, h in _RESOLUTIONS if responsive_scale(w, h) < MAX_SCALE]
        capacities = [
            visible_chars(w, font_sizes(responsive_scale(w, h))["expression"])
            for w, h in unclamped
        ]
        self.assertLessEqual(
            max(capacities) - min(capacities), 6,
            f"capacidade variou demais entre {unclamped}: {capacities}",
        )

    def test_very_large_screen_fits_more_once_the_font_is_capped(self) -> None:
        """At 4K the font stops growing (MAX_SCALE), so the extra width turns
        into extra characters rather than oversized text."""
        full_hd = visible_chars(1920, font_sizes(responsive_scale(1920, 1080))["expression"])
        uhd = visible_chars(3840, font_sizes(responsive_scale(3840, 2160))["expression"])
        self.assertGreater(uhd, full_hd)

    def test_shows_more_than_the_lcd_hard_coded_limit(self) -> None:
        """The LCD front truncates the expression at a fixed 30 chars; on a
        monitor the limit must come from the real width and be at least as good."""
        for width, height in [(1366, 768), (1920, 1080)]:
            capacity = visible_chars(width, font_sizes(responsive_scale(width, height))["expression"])
            self.assertGreater(capacity, 30, f"{width}x{height} coube menos que o LCD fixo")

    def test_always_leaves_a_usable_minimum(self) -> None:
        self.assertGreaterEqual(visible_chars(1, 200), 8)


if __name__ == "__main__":
    unittest.main()
