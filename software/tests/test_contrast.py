import unittest

from software.ui.shared.contrast import contrast_ratio, hex_to_rgb, meets_wcag_aa
from software.ui.shared.palette import BUTTON_PALETTE, DISPLAY_BACKGROUND, DISPLAY_FOREGROUND


class ContrastRatioTest(unittest.TestCase):
    def test_black_on_white_is_maximum_contrast(self) -> None:
        self.assertAlmostEqual(contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=1)

    def test_identical_colors_have_ratio_one(self) -> None:
        self.assertAlmostEqual(contrast_ratio((100, 100, 100), (100, 100, 100)), 1.0, places=6)

    def test_meets_wcag_aa_thresholds(self) -> None:
        # Contraste conhecido baixo (laranja vivo x branco): falha para texto normal.
        low_contrast_orange = (243, 156, 18)
        white = (255, 255, 255)
        self.assertFalse(meets_wcag_aa(low_contrast_orange, white, large_text=False))

        # Preto x branco sempre passa em qualquer critério.
        self.assertTrue(meets_wcag_aa((0, 0, 0), (255, 255, 255), large_text=False))
        self.assertTrue(meets_wcag_aa((0, 0, 0), (255, 255, 255), large_text=True))


class ButtonPaletteWcagTest(unittest.TestCase):
    """Every category color pair must clear WCAG AA (large text: every label
    in this UI is >=28pt bold, above the 14pt-bold/18pt-regular threshold)."""

    def test_every_category_meets_wcag_aa_large_text(self) -> None:
        for name, colors in BUTTON_PALETTE.items():
            bg = hex_to_rgb(colors.background)
            fg = hex_to_rgb(colors.foreground)
            ratio = contrast_ratio(bg, fg)
            self.assertTrue(
                meets_wcag_aa(bg, fg, large_text=True),
                f"categoria '{name}' tem contraste {ratio:.2f}, abaixo do mínimo AA (3.0)",
            )

    def test_every_category_meets_wcag_aa_normal_text(self) -> None:
        """Extra margin: aim for the stricter normal-text threshold too."""
        for name, colors in BUTTON_PALETTE.items():
            bg = hex_to_rgb(colors.background)
            fg = hex_to_rgb(colors.foreground)
            ratio = contrast_ratio(bg, fg)
            self.assertTrue(
                meets_wcag_aa(bg, fg, large_text=False),
                f"categoria '{name}' tem contraste {ratio:.2f}, abaixo do critério normal AA (4.5)",
            )

    def test_display_meets_wcag_aa(self) -> None:
        bg = hex_to_rgb(DISPLAY_BACKGROUND)
        fg = hex_to_rgb(DISPLAY_FOREGROUND)
        self.assertTrue(meets_wcag_aa(bg, fg, large_text=True))


if __name__ == "__main__":
    unittest.main()
