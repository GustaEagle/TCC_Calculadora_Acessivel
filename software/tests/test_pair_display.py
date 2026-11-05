"""Exibição de um PAR de coordenadas na tela.

Defeito relatado em bancada: "aparecem dois pontos (..) indevidamente" e "a
calculadora anuncia X e Y por áudio, mas não exibe X no LCD".

Era a mesma causa. O par ia para a tela como uma linha só - "(5, 53.13010235)",
16 caracteres - acima do MAX_RESULT_CHARS de 14, e a truncagem ficava com a
CAUDA: o utilizador via "..53.13010235)". Os ".." eram a marca de corte e o
primeiro valor desaparecia por completo.

Agora o par vai em duas linhas rotuladas e a truncagem preserva a cabeça.
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine
from software.core.models import VALUE_KIND_POLAR, VALUE_KIND_RECTANGULAR
from software.ui.shared.formatting import (
    clip_display_line,
    format_pair_for_display,
    format_result_for_display,
    is_pair_result,
)


class PairDisplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_polar_pair_is_two_labelled_lines(self) -> None:
        text = format_result_for_display(self.engine.evaluate("polar(3, 4)"))
        self.assertEqual(text, "r = 5\nθ = 53.13010235")

    def test_rectangular_pair_is_two_labelled_lines(self) -> None:
        text = format_result_for_display(self.engine.evaluate("rect(2, 60)"))
        self.assertEqual(text, "x = 1\ny = 1.732050808")

    def test_both_components_are_present(self) -> None:
        """O X deixou de ser cortado: as duas componentes estão no texto."""
        for expression in ("polar(3, 4)", "rect(2, 60)", "polar(0, 1)"):
            with self.subTest(expression=expression):
                result = self.engine.evaluate(expression)
                text = format_result_for_display(result)
                self.assertEqual(len(text.split("\n")), 2)
                for component in result.value:
                    self.assertIn(f"{component:.10g}", text)

    def test_no_truncation_marker_for_a_pair(self) -> None:
        """Cada linha cabe no limite, então não há ".." nenhum."""
        for expression in ("polar(3, 4)", "rect(2, 60)", "polar(1234, 5678)"):
            with self.subTest(expression=expression):
                text = format_result_for_display(self.engine.evaluate(expression))
                for line in text.split("\n"):
                    self.assertLessEqual(len(line), 26)
                    self.assertNotIn("..", line)

    def test_labels_follow_the_conversion_direction(self) -> None:
        self.assertEqual(
            format_pair_for_display((5.0, 53.13), VALUE_KIND_POLAR),
            "r = 5\nθ = 53.13",
        )
        self.assertEqual(
            format_pair_for_display((3.0, 4.0), VALUE_KIND_RECTANGULAR),
            "x = 3\ny = 4",
        )

    def test_display_keeps_scalar_results_untouched(self) -> None:
        result = self.engine.evaluate("2+2")
        self.assertFalse(is_pair_result(result))
        self.assertEqual(format_result_for_display(result), "4")

    def test_errors_are_not_treated_as_pairs(self) -> None:
        result = self.engine.evaluate("polar(5, 30, 2)")
        self.assertFalse(is_pair_result(result))
        self.assertEqual(format_result_for_display(result), result.display)

    def test_pair_display_matches_the_announced_precision(self) -> None:
        """A tela não pode dizer menos do que a voz anuncia."""
        from software.ui.shared.speech_text import spoken_pair

        result = self.engine.evaluate("polar(3, 4)")
        text = format_result_for_display(result)
        spoken = spoken_pair(result.value, result.value_kind)
        # "53.13010235" na tela e "53 ponto 1 3 0 1 0 2 3 5" na voz: os mesmos
        # dígitos. A parte INTEIRA é falada junta (o motor de voz já a lê como
        # cardinal); só a fracionária é lida dígito a dígito.
        self.assertIn("53.13010235", text)
        self.assertIn("53 ponto 1 3 0 1 0 2 3 5", spoken)


class ClipDisplayLineTests(unittest.TestCase):
    """A truncagem preserva a CABEÇA: num número é a ordem de grandeza e os
    primeiros dígitos que importam. Cortar o início lia-se como outro número."""

    def test_short_lines_are_untouched(self) -> None:
        self.assertEqual(clip_display_line("x = 3", 14), "x = 3")

    def test_exactly_at_the_limit_is_untouched(self) -> None:
        self.assertEqual(clip_display_line("1234567890", 10), "1234567890")

    def test_long_lines_keep_the_head(self) -> None:
        self.assertEqual(clip_display_line("53364.75335", 9), "53364.7..")

    def test_the_marker_never_replaces_everything(self) -> None:
        self.assertTrue(clip_display_line("123456", 2).startswith("1"))


if __name__ == "__main__":
    unittest.main()
