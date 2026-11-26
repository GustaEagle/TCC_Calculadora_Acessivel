"""Multiplicação implícita, o caso "2e3" e o Ans protegido (T07).

Um operando colado a outro multiplica, como numa calculadora comercial. A
prioridade contra a divisão (1/2(3)) está em aberto até a equipe definir a
calculadora de referência, e por isso não é fixada aqui.
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine


class ImplicitMultiplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def assertDisplay(self, expression: str, expected: str, ans: float | None = None) -> None:
        result = self.engine.evaluate(expression, ans)
        self.assertTrue(result.ok, msg=f"{expression}: {result.display}")
        self.assertEqual(result.display, expected)

    def test_number_before_parenthesis(self) -> None:
        self.assertDisplay("2(3)", "6")

    def test_number_before_group_with_operation(self) -> None:
        self.assertDisplay("2(3+4)", "14")

    def test_number_before_function(self) -> None:
        self.assertDisplay("2sqrt(9)", "6")

    def test_group_before_group(self) -> None:
        self.assertDisplay("(2)(3)", "6")

    def test_function_before_group(self) -> None:
        self.assertDisplay("sqrt(4)(2)", "4")

    def test_number_before_constant(self) -> None:
        self.assertDisplay("2π", "6.283185307")

    def test_number_before_previous_answer(self) -> None:
        """"3Ans": entre o dígito e o "A" não há fronteira de palavra, e o Ans
        escapava à substituição."""
        self.assertDisplay("3Ans", "12", ans=4)

    def test_previous_answer_before_parenthesis(self) -> None:
        self.assertDisplay("Ans(2)", "8", ans=4)

    def test_power_binds_tighter_than_implicit_multiplication(self) -> None:
        self.assertDisplay("2Ans^2", "18", ans=-3)

    def test_function_call_gets_no_spurious_multiplication(self) -> None:
        self.assertDisplay("sin(30)", "0.5")

    def test_exp_key_and_ncr_are_unchanged(self) -> None:
        self.assertDisplay("3exp(8)", "300000000")
        self.assertDisplay("5 nCr 2", "10")
        self.assertDisplay("5nCr2", "10")

    def test_functional_ncr_is_still_rejected(self) -> None:
        self.assertEqual(self.engine.evaluate("nCr(5,2)").code, "ERR-007")

    def test_autoclose_still_works(self) -> None:
        self.assertDisplay("2sqrt(9", "6")


class ScientificLiteralTests(unittest.TestCase):
    """"2e3" é 2 x e x 3. Antes dava 2000 sem aviso: o Python lia notação
    científica. A potência de dez tem tecla própria (EXP)."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_reported_case(self) -> None:
        result = self.engine.evaluate("2e3")
        self.assertEqual(result.display, "16.30969097")
        self.assertNotEqual(result.display, "2000")

    def test_other_exponent_literal(self) -> None:
        self.assertEqual(self.engine.evaluate("1e5").display, "13.59140914")

    def test_number_followed_only_by_the_constant(self) -> None:
        self.assertEqual(self.engine.evaluate("2e").display, "5.436563657")

    def test_power_of_e_unchanged(self) -> None:
        self.assertEqual(self.engine.evaluate("e^2").display, "7.389056099")

    def test_power_of_ten_by_the_exp_key(self) -> None:
        self.assertEqual(self.engine.evaluate("2exp(3)").display, "2000")


class ProtectedPreviousAnswerTests(unittest.TestCase):
    """Ans entra como constante, e não colado no texto."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_negative_answer_squared(self) -> None:
        """Colado no texto, "-3.0**2" dava -9: o menos saía do grupo."""
        self.assertEqual(self.engine.evaluate("Ans^2", -3).display, "9")

    def test_large_answer_is_not_re_tokenized(self) -> None:
        """str(1e20) = "1e+20" seria lido como 1*e+20 pela multiplicação
        implícita."""
        self.assertAlmostEqual(self.engine.evaluate("Ans*2", 1e20).value, 2e20)

    def test_small_answer_keeps_its_value(self) -> None:
        self.assertAlmostEqual(self.engine.evaluate("Ans*2", 1e-5).value, 2e-5)

    def test_factorial_and_percentage_of_answer(self) -> None:
        self.assertEqual(self.engine.evaluate("Ans!", 5).display, "120")
        self.assertEqual(self.engine.evaluate("Ans%", 50).display, "0.5")

    def test_inverse_of_answer(self) -> None:
        self.assertEqual(self.engine.evaluate("inv", 4).display, "0.25")

    def test_missing_answer_still_warns(self) -> None:
        self.assertEqual(self.engine.evaluate("3Ans").code, "WRN-010")


if __name__ == "__main__":
    unittest.main()
