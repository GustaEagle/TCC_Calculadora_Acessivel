import pathlib
import unittest

from software.hw_platform.keyboard import KeyboardAdapter
from software.ui.shared.keypad import (
    HISTORY_TOKEN,
    RIGHT_BUTTONS,
    SPOKEN_TOKEN_NAMES,
)


def _front_source(front: str) -> str:
    path = pathlib.Path(__file__).resolve().parents[1] / "ui" / front / "app.py"
    return path.read_text(encoding="utf-8")


class HistoryShortcutTest(unittest.TestCase):
    """Histórico abre por teclado (Ctrl + Ans), nunca por botão dedicado."""

    def test_ans_key_carries_history_as_its_ctrl_function(self) -> None:
        ans = [item for row in RIGHT_BUTTONS for item in row if item[1] == "Ans"]
        self.assertEqual(len(ans), 1, "tecla Ans não encontrada no teclado")
        self.assertEqual(ans[0][2], HISTORY_TOKEN, "Ctrl + Ans não abre o histórico")

    def test_history_token_has_a_spoken_name(self) -> None:
        self.assertIn(HISTORY_TOKEN, SPOKEN_TOKEN_NAMES)

    def test_pc_keyboard_can_reach_the_ans_key(self) -> None:
        """A matriz 6x7 tem tecla Ans; num PC 'a' ocupa esse lugar, senão o
        atalho seria intestável fora do hardware."""
        self.assertEqual(KeyboardAdapter().map_key("a"), "Ans")

    def test_neither_front_offers_a_history_button(self) -> None:
        for front in ("lcd", "hdmi"):
            source = _front_source(front)
            self.assertNotIn(
                'text="Histórico"', source,
                f"front '{front}' ainda tem botão de histórico",
            )
            self.assertNotIn("_show_history", source, f"front '{front}' com diálogo por botão")

    def test_both_fronts_handle_the_history_token(self) -> None:
        for front in ("lcd", "hdmi"):
            self.assertIn(
                "HISTORY_TOKEN", _front_source(front),
                f"front '{front}' não trata o atalho do histórico",
            )


class NoOutputDiagnosticsTest(unittest.TestCase):
    """A interface não exibe qual saída de vídeo/energia está em uso."""

    def test_fronts_do_not_show_the_active_output(self) -> None:
        for front in ("lcd", "hdmi"):
            source = _front_source(front)
            for texto in ("Saida visual", "Saída visual", "Monitor HDMI", "Modo local"):
                self.assertNotIn(
                    texto, source, f"front '{front}' ainda exibe diagnóstico '{texto}'",
                )

    def test_fronts_do_not_render_ups_state(self) -> None:
        for front in ("lcd", "hdmi"):
            source = _front_source(front)
            self.assertNotIn("UpsMonitor", source, f"front '{front}' ainda exibe energia")


class FixedSizeWindowTest(unittest.TestCase):
    """Ambos os fronts usam janela de tamanho fixo (padrão Windows)."""

    def test_both_fronts_are_not_resizable(self) -> None:
        for front in ("lcd", "hdmi"):
            source = _front_source(front)
            self.assertIn(
                "resizable(False, False)", source,
                f"front '{front}' ainda redimensiona",
            )

    def test_hdmi_no_longer_recomputes_layout_on_resize(self) -> None:
        source = _front_source("hdmi")
        self.assertNotIn("<Configure>", source)
        self.assertNotIn("_apply_scale", source)


if __name__ == "__main__":
    unittest.main()
