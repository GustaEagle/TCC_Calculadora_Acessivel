"""A composição do front HDMI é escolhida pelo tamanho REAL da tela.

O monitor externo não tem resolução conhecida, então o front decide na
construção o que cabe: teclado e histórico são omitidos quando não há espaço
(como na calculadora do Windows), e a tipografia acompanha a resolução.

Estes testes exercitam só as funções puras de ui/shared/layout.py — de
propósito: eles precisam rodar sem DISPLAY, ao contrário dos testes que
instanciam ttkbootstrap e exigem Xvfb no CI.
"""

import unittest

from software.ui.shared.layout import (
    BASE_FONT_SIZES,
    LEGIBILITY_FLOORS,
    BASE_MAX_EXPRESSION_CHARS,
    HISTORY_MIN_HEIGHT,
    HISTORY_MIN_WIDTH,
    KEYPAD_MIN_HEIGHT,
    KEYPAD_MIN_WIDTH,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SCALE_CEILING,
    SCALE_FLOOR,
    LayoutTier,
    display_limits,
    font_sizes,
    scale_for,
    tier_for,
)


class TierSelectionTest(unittest.TestCase):
    def test_large_monitor_gets_the_full_composition(self) -> None:
        self.assertIs(tier_for(1920, 1080), LayoutTier.FULL)

    def test_mid_monitor_keeps_the_keypad_but_drops_history(self) -> None:
        self.assertIs(tier_for(1024, 768), LayoutTier.MEDIUM)

    def test_small_monitor_shows_only_the_display(self) -> None:
        self.assertIs(tier_for(800, 600), LayoutTier.COMPACT)

    def test_keypad_threshold_is_inclusive(self) -> None:
        """No limiar exato o teclado já aparece - o limiar é o mínimo aceito."""
        self.assertIs(tier_for(KEYPAD_MIN_WIDTH, KEYPAD_MIN_HEIGHT), LayoutTier.MEDIUM)

    def test_one_pixel_below_the_keypad_threshold_drops_it(self) -> None:
        self.assertIs(tier_for(KEYPAD_MIN_WIDTH - 1, KEYPAD_MIN_HEIGHT), LayoutTier.COMPACT)
        self.assertIs(tier_for(KEYPAD_MIN_WIDTH, KEYPAD_MIN_HEIGHT - 1), LayoutTier.COMPACT)

    def test_history_threshold_is_inclusive(self) -> None:
        self.assertIs(tier_for(HISTORY_MIN_WIDTH, HISTORY_MIN_HEIGHT), LayoutTier.FULL)

    def test_one_pixel_below_the_history_threshold_drops_it(self) -> None:
        self.assertIs(tier_for(HISTORY_MIN_WIDTH - 1, HISTORY_MIN_HEIGHT), LayoutTier.MEDIUM)
        self.assertIs(tier_for(HISTORY_MIN_WIDTH, HISTORY_MIN_HEIGHT - 1), LayoutTier.MEDIUM)

    def test_wide_but_short_screen_gets_no_keypad(self) -> None:
        """Area de sobra nao basta: o teclado tem 6 linhas e precisa de ALTURA."""
        self.assertIs(tier_for(1920, 480), LayoutTier.COMPACT)

    def test_tall_but_narrow_screen_gets_no_keypad(self) -> None:
        """Espelho do caso anterior: 7 colunas precisam de LARGURA."""
        self.assertIs(tier_for(600, 1920), LayoutTier.COMPACT)


class TierCapabilitiesTest(unittest.TestCase):
    """As faixas sao consultadas por intencao, nao por comparacao de enum."""

    def test_only_full_shows_history(self) -> None:
        self.assertTrue(LayoutTier.FULL.shows_history)
        self.assertFalse(LayoutTier.MEDIUM.shows_history)
        self.assertFalse(LayoutTier.COMPACT.shows_history)

    def test_history_tier_also_shows_the_keypad(self) -> None:
        """Nao existe faixa com historico e sem teclado."""
        self.assertTrue(LayoutTier.FULL.shows_keypad)
        self.assertTrue(LayoutTier.MEDIUM.shows_keypad)
        self.assertFalse(LayoutTier.COMPACT.shows_keypad)


class ScaleTest(unittest.TestCase):
    def test_reference_resolution_scales_by_one(self) -> None:
        self.assertAlmostEqual(scale_for(REFERENCE_WIDTH, REFERENCE_HEIGHT), 1.0)

    def test_scale_follows_the_smaller_axis(self) -> None:
        """Ultrawide: a largura sobra, a altura manda - senao a fonte estoura."""
        self.assertAlmostEqual(scale_for(3840, 1080), 1080 / REFERENCE_HEIGHT)

    def test_tiny_screen_is_clamped_by_the_floor(self) -> None:
        self.assertAlmostEqual(scale_for(640, 480), SCALE_FLOOR)

    def test_4k_is_clamped_by_the_ceiling(self) -> None:
        self.assertAlmostEqual(scale_for(3840, 2160), SCALE_CEILING)

    def test_unreportable_screen_falls_back_to_the_reference(self) -> None:
        """Tk que nao consiga informar a tela nao pode gerar fonte invalida."""
        self.assertAlmostEqual(scale_for(0, 0), 1.0)


class FontSizesTest(unittest.TestCase):
    def test_reference_scale_reproduces_the_previous_fixed_table(self) -> None:
        """Nao-regressao: em 1280x720 a aparencia e' exatamente a de antes."""
        self.assertEqual(font_sizes(1.0), BASE_FONT_SIZES)

    def test_larger_scale_grows_every_font(self) -> None:
        bigger = font_sizes(2.0)
        for name, base in BASE_FONT_SIZES.items():
            self.assertGreater(bigger[name], base, f"fonte {name} nao cresceu")

    def test_fonts_never_collapse_to_zero(self) -> None:
        for size in font_sizes(SCALE_FLOOR).values():
            self.assertGreaterEqual(size, 1)

    def test_fonts_never_fall_below_their_legibility_floor(self) -> None:
        """PRD §4: encolher a tela nao pode tornar o texto inutil para visao parcial.

        Recupera uma garantia que existia em test_responsive_layout.py e se
        perdeu quando aquele ficheiro foi removido ao fixar a janela.
        """
        tiny = font_sizes(SCALE_FLOOR)
        for role, floor in LEGIBILITY_FLOORS.items():
            self.assertGreaterEqual(tiny[role], floor, f"fonte '{role}' ficou ilegivel")

    def test_an_extreme_scale_still_respects_the_floor(self) -> None:
        """O piso vale mesmo se alguem baixar o SCALE_FLOOR um dia."""
        for role, floor in LEGIBILITY_FLOORS.items():
            self.assertGreaterEqual(font_sizes(0.01)[role], floor)

    def test_result_stays_the_most_prominent_text(self) -> None:
        """A hierarquia visual resultado > expressao > botao vale em toda escala."""
        for width, height in [(800, 480), (1280, 720), (1366, 768), (1920, 1080), (3840, 2160)]:
            sizes = font_sizes(scale_for(width, height))
            self.assertGreater(
                sizes["result"], sizes["expression"],
                f"resultado deixou de dominar em {width}x{height}",
            )
            self.assertGreater(sizes["expression"], sizes["button"])


class DisplayLimitsTest(unittest.TestCase):
    def test_reference_resolution_keeps_the_previous_limits(self) -> None:
        expression, _ = display_limits(REFERENCE_WIDTH, 1.0)
        self.assertEqual(expression, BASE_MAX_EXPRESSION_CHARS)

    def test_bigger_font_on_the_same_screen_fits_fewer_characters(self) -> None:
        same_width_small_font = display_limits(REFERENCE_WIDTH, 1.0)[0]
        same_width_big_font = display_limits(REFERENCE_WIDTH, 2.0)[0]
        self.assertLess(same_width_big_font, same_width_small_font)

    def test_4k_fits_more_text_because_the_font_is_capped(self) -> None:
        """A janela cresce 3x e a fonte para em 2x: cabe MAIS, nao menos."""
        wide, _ = display_limits(3840, scale_for(3840, 2160))
        self.assertGreater(wide, BASE_MAX_EXPRESSION_CHARS)

    def test_limits_never_reach_zero(self) -> None:
        expression, result = display_limits(1, SCALE_CEILING)
        self.assertGreaterEqual(expression, 1)
        self.assertGreaterEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
