"""O front HDMI monta exatamente os paineis que a sua faixa promete.

As regras em si (limiares, escala) sao testadas sem display em
test_hdmi_layout_tiers.py. Aqui o que se verifica e' a LIGACAO: que o front
consulta a faixa e constroi de acordo, e que nao sobra referencia pendente
quando um painel nao e' montado.

Nao se fixa uma resolucao esperada de proposito - a tela e' a da maquina (ou a
do Xvfb no CI). As asercoes sao condicionais a faixa que o front escolheu, o
que torna o teste valido em qualquer monitor.
"""

import unittest
from unittest import mock

from software.ui.hdmi.app import CalculatorApp
from software.ui.shared.layout import (
    LayoutTier,
    display_limits,
    font_sizes,
    scale_for,
    tier_for,
)


class HdmiLayoutWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = CalculatorApp()
        self.addCleanup(self.app.root.destroy)

    def test_tier_and_scale_come_from_the_screen_the_front_measured(self) -> None:
        self.assertIs(
            self.app.tier, tier_for(self.app.screen_width, self.app.screen_height)
        )
        self.assertAlmostEqual(
            self.app.scale, scale_for(self.app.screen_width, self.app.screen_height)
        )

    def test_fonts_and_limits_follow_the_chosen_scale(self) -> None:
        self.assertEqual(self.app.fonts, font_sizes(self.app.scale))
        expected = display_limits(self.app.screen_width, self.app.scale)
        self.assertEqual(
            (self.app.max_expression_chars, self.app.max_result_chars), expected
        )

    def test_keypad_exists_exactly_when_the_tier_says_so(self) -> None:
        if self.app.tier.shows_keypad:
            self.assertIsNotNone(self.app.keypad_frame)
            self.assertTrue(self.app.buttons, "faixa com teclado nao criou botoes")
        else:
            self.assertIsNone(self.app.keypad_frame)
            self.assertFalse(self.app.buttons, "faixa sem teclado criou botoes")

    def test_toggle_button_follows_the_keypad(self) -> None:
        """Sem teclado nao pode haver botao de alternar teclado."""
        self.assertEqual(self.app.toggle_btn is not None, self.app.tier.shows_keypad)

    def test_history_panel_exists_exactly_when_the_tier_says_so(self) -> None:
        self.assertEqual(
            self.app.history_frame is not None, self.app.tier.shows_history
        )

    def test_display_is_built_in_every_tier(self) -> None:
        """Expressao e resultado sao o minimo: nenhuma faixa os omite."""
        self.assertIsNotNone(self.app.expression_label)
        self.assertIsNotNone(self.app.result_label)

    def test_window_stays_fixed_size(self) -> None:
        """A decisao e' tomada uma vez: nao ha caminho de resize."""
        self.assertEqual(self.app.root.resizable(), (False, False))


class HdmiCompactTierToleranceTest(unittest.TestCase):
    """Os metodos que tocam teclado/historico toleram a faixa compacta.

    Simula a faixa compacta esvaziando as referencias do front ja construido:
    e' o estado em que ele nasceria num monitor pequeno, e nenhum destes
    caminhos pode estourar (o app segue operavel pelo teclado fisico, RF-05).
    """

    def setUp(self) -> None:
        self.app = CalculatorApp()
        self.addCleanup(self.app.root.destroy)
        self.app.keypad_frame = None
        self.app.toggle_btn = None
        self.app.history_frame = None
        self.app.buttons = {}

    def test_refresh_history_without_panel_is_a_no_op(self) -> None:
        self.app._refresh_history()

    def test_apply_controls_visibility_without_keypad_is_a_no_op(self) -> None:
        self.app._apply_controls_visibility()

    def test_initial_focus_falls_back_to_the_window(self) -> None:
        self.app._set_initial_focus()

    def test_keypad_labels_update_without_buttons(self) -> None:
        self.app._update_keypad_labels()


class HdmiScreenSourceTest(unittest.TestCase):
    """De onde o front tira o tamanho da tela (RF-09).

    O monitor externo entra sempre com a calculadora ja ligada, entao este front
    nasce logo depois de o xrandr trocar de painel - o momento exato em que o
    valor do Tk esta velho. Confiar nele fazia a janela subir no tamanho do LCD,
    e portanto na faixa compacta: sem teclado e sem historico.
    """

    def test_xrandr_wins_over_the_cached_tk_value(self) -> None:
        with mock.patch(
            "software.hw_platform.video_output.screen_size", return_value=(1920, 1080)
        ):
            app = CalculatorApp()
            self.addCleanup(app.root.destroy)

        self.assertEqual((app.screen_width, app.screen_height), (1920, 1080))
        self.assertIs(app.tier, LayoutTier.FULL)
        self.assertIsNotNone(app.keypad_frame)
        self.assertIsNotNone(app.history_frame)

    def test_a_stale_small_screen_would_have_produced_the_compact_tier(self) -> None:
        """Prova a regressao: o valor velho do LCD leva mesmo a faixa compacta."""
        with mock.patch(
            "software.hw_platform.video_output.screen_size", return_value=(800, 480)
        ):
            app = CalculatorApp()
            self.addCleanup(app.root.destroy)

        self.assertIs(app.tier, LayoutTier.COMPACT)
        self.assertIsNone(app.keypad_frame)
        self.assertIsNone(app.history_frame)

    def test_falls_back_to_tk_when_xrandr_cannot_answer(self) -> None:
        """Fora do Pi nao ha xrandr - e ai o valor do Tk esta correto."""
        with mock.patch(
            "software.hw_platform.video_output.screen_size", return_value=None
        ):
            app = CalculatorApp()
            self.addCleanup(app.root.destroy)

        self.assertEqual(
            (app.screen_width, app.screen_height),
            (app.root.winfo_screenwidth(), app.root.winfo_screenheight()),
        )


if __name__ == "__main__":
    unittest.main()
