"""nCr/nPr em notação infixa (expression-normalization).

A tecla "nCr" fica ENTRE os operandos, como numa calculadora científica: a
sequência física é 5, nCr, 2, =. A forma funcional nCr(5,2) deixou de ser
aceita (BREAKING) - ver proposal.md e design.md §3.
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine


class InfixCombinatoricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_combination_from_physical_key_sequence(self) -> None:
        self.assertEqual(self.engine.evaluate("5 nCr 2").display, "10")

    def test_combination_without_spaces(self) -> None:
        self.assertEqual(self.engine.evaluate("5nCr2").display, "10")

    def test_permutation_from_physical_key_sequence(self) -> None:
        self.assertEqual(self.engine.evaluate("5 nPr 2").display, "20")

    def test_case_insensitive(self) -> None:
        self.assertEqual(self.engine.evaluate("5 NCR 2").display, "10")

    def test_binds_tighter_than_addition(self) -> None:
        self.assertEqual(self.engine.evaluate("2 + 5 nCr 2").display, "12")

    def test_parenthesised_groups_as_operands(self) -> None:
        self.assertEqual(self.engine.evaluate("(4+1) nCr (1+1)").display, "10")

    def test_function_call_as_left_operand(self) -> None:
        """"sqrt(25)" é UM átomo, não "sqrt" seguido de "(25)"."""
        self.assertEqual(self.engine.evaluate("sqrt(25) nCr 2").display, "10")

    def test_previous_answer_as_operand(self) -> None:
        self.assertEqual(self.engine.evaluate("Ans nCr 2", 5).display, "10")

    def test_negative_previous_answer_keeps_unary_minus_outside(self) -> None:
        """O sinal fica FORA do átomo: "-5 nCr 2" é -(5 nCr 2), consistente
        com a precedência do menos unário no resto do motor."""
        self.assertEqual(self.engine.evaluate("Ans nCr 2", -5).display, "-10")


class InfixCombinatoricsLimitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_n_equals_r(self) -> None:
        self.assertEqual(self.engine.evaluate("5 nCr 5").display, "1")

    def test_r_equals_zero(self) -> None:
        self.assertEqual(self.engine.evaluate("5 nCr 0").display, "1")

    def test_n_smaller_than_r(self) -> None:
        self.assertEqual(self.engine.evaluate("2 nCr 5").code, "ERR-004")

    def test_negative_operand(self) -> None:
        """O sinal entra no átomo da DIREITA, então chega ao domínio como -2
        e devolve ERR-004 em vez de parecer entrada truncada."""
        self.assertEqual(self.engine.evaluate("5 nCr -2").code, "ERR-004")

    def test_non_integer_operand(self) -> None:
        self.assertEqual(self.engine.evaluate("5.5 nCr 2").code, "ERR-004")

    def test_missing_right_operand_is_incomplete(self) -> None:
        result = self.engine.evaluate("5 nCr")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")

    def test_missing_left_operand_is_incomplete(self) -> None:
        result = self.engine.evaluate("nCr 2")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")


class FunctionalFormRejectedTests(unittest.TestCase):
    """BREAKING: nCr(5,2) deixou de calcular."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_functional_combination_rejected(self) -> None:
        self.assertEqual(self.engine.evaluate("nCr(5,2)").code, "ERR-007")

    def test_functional_permutation_rejected(self) -> None:
        self.assertEqual(self.engine.evaluate("nPr(10,3)").code, "ERR-007")


class AutoCloseBeforeInfixTests(unittest.TestCase):
    """O fecho corre ANTES da reescrita infixa (design.md §2), para que a
    procura dos operandos nunca encontre um grupo sem fecho."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_unclosed_function_around_infix_operator(self) -> None:
        # O fecho cai no fim, logo a combinação fica DENTRO da raiz:
        # sqrt(9 nCr 2) = sqrt(36) = 6.
        self.assertEqual(self.engine.evaluate("sqrt(9 nCr 2").display, "6")

    def test_unclosed_group_as_right_operand(self) -> None:
        self.assertEqual(self.engine.evaluate("5 nCr (2").display, "10")


if __name__ == "__main__":
    unittest.main()
