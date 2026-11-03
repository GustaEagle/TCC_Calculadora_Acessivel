from __future__ import annotations

import unittest

from software.core import CalculationEngine


class CalculationEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_basic_arithmetic(self) -> None:
        result = self.engine.evaluate("2+3*4")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "14")

    def test_scientific_functions_use_degrees(self) -> None:
        result = self.engine.evaluate("sen(30)+cos(60)")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "1")

    def test_division_by_zero_error_code(self) -> None:
        result = self.engine.evaluate("1/0")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "ERR-001")

    def test_ans_without_previous_value_warns(self) -> None:
        result = self.engine.evaluate("Ans+1")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "WRN-010")
        self.assertEqual(result.priority, "P2")

    def test_combinatorics(self) -> None:
        # Notação INFIXA: a forma funcional nCr(5,2) deixou de ser aceita
        # (ver test_combinatorics_infix.py).
        result = self.engine.evaluate("5 nCr 2 + 4 nPr 2")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "22")


class ArityTests(unittest.TestCase):
    """PRD §13: argumentos a menos é entrada INCOMPLETA (P2), não inválida.

    Sem esta validação, o TypeError do Python escapava como ERR-007 com a
    mensagem em inglês - que o TTS leria em voz alta.
    """

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_conversion_missing_argument_is_incomplete(self) -> None:
        result = self.engine.evaluate("polar(5")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")

    def test_logbase_missing_argument_is_incomplete(self) -> None:
        result = self.engine.evaluate("logbase(2")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")

    def test_conversion_with_extra_arguments_is_err_009(self) -> None:
        self.assertEqual(self.engine.evaluate("polar(5, 30, 2)").code, "ERR-009")
        self.assertEqual(self.engine.evaluate("rect(3, 4, 5)").code, "ERR-009")

    def test_other_function_with_extra_arguments_is_syntax_error(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt(4, 5)").code, "ERR-007")

    def test_empty_expression_stays_incomplete(self) -> None:
        result = self.engine.evaluate("")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")


if __name__ == "__main__":
    unittest.main()
