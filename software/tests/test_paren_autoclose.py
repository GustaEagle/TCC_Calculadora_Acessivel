"""Fecho automático de parênteses (expression-normalization).

Numa calculadora física o utilizador pressiona "√", "1", "4", "4", "=" e nunca
pressiona o fecho, então o fecho implícito é o caso normal. O fecho órfão -
um ")" sem abertura - continua a ser ERR-007, porque não tem leitura única.
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine


class ParenthesisAutoCloseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_function_without_closing(self) -> None:
        result = self.engine.evaluate("sqrt(144")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "12")

    def test_arithmetic_group_without_closing(self) -> None:
        self.assertEqual(self.engine.evaluate("(2+3").display, "5")

    def test_two_levels_missing(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt((4").display, "2")

    def test_partial_deficit_leaves_closed_group_intact(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt(16)+(2*3").display, "10")

    def test_autoclose_runs_after_percentage_rewrite(self) -> None:
        """O "(50%" vira "((50/100)": o fecho tem de contar o parêntese que a
        reescrita da percentagem introduziu, e por isso corre no FIM."""
        self.assertEqual(self.engine.evaluate("(50%").display, "0.5")

    def test_balanced_expression_unchanged(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt(144)").display, "12")


class OrphanClosingParenthesisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_closing_without_opening(self) -> None:
        result = self.engine.evaluate("2+)")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "ERR-007")
        self.assertEqual(result.priority, "P1")

    def test_extra_closing_after_valid_group(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt(4))").code, "ERR-007")

    def test_orphan_close_blocks_autoclose_of_pending_open(self) -> None:
        """Há um "(" pendente, mas também um ")" órfão: NÃO se fecha nada."""
        self.assertEqual(self.engine.evaluate(")2+(3").code, "ERR-007")


class OriginalExpressionPreservedTests(unittest.TestCase):
    def test_result_keeps_what_the_user_typed(self) -> None:
        """O fecho é detalhe da avaliação; a linha de cálculo não é reescrita."""
        result = CalculationEngine().evaluate("sqrt(144")
        self.assertEqual(result.expression, "sqrt(144")


if __name__ == "__main__":
    unittest.main()
