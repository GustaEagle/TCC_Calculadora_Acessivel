import unittest

from software.core import CalculationEngine, CalculatorState
from software.ui_lcd.formatting import format_expression_for_display


class ExpressionDisplayTest(unittest.TestCase):
    def test_sqrt_uses_conventional_symbol(self) -> None:
        self.assertEqual(format_expression_for_display("sqrt(4)"), "√(4)")

    def test_inv_uses_conventional_symbol(self) -> None:
        self.assertEqual(format_expression_for_display("inv(2)"), "x⁻¹(2)")

    def test_logbase_uses_conventional_symbol(self) -> None:
        self.assertEqual(format_expression_for_display("logbase(2, 8)"), "log_b(2, 8)")

    def test_inverse_trig_uses_conventional_symbols(self) -> None:
        self.assertEqual(format_expression_for_display("asin(0.5)"), "sen⁻¹(0.5)")
        self.assertEqual(format_expression_for_display("acos(0.5)"), "cos⁻¹(0.5)")
        self.assertEqual(format_expression_for_display("atan(1)"), "tan⁻¹(1)")

    def test_rect_uses_conventional_symbol(self) -> None:
        self.assertEqual(format_expression_for_display("rect(3, 4)"), "Rec(3, 4)")

    def test_untouched_tokens_pass_through(self) -> None:
        self.assertEqual(format_expression_for_display("2+2*sen(30)"), "2+2*sen(30)")

    def test_nested_functions_all_replaced(self) -> None:
        self.assertEqual(
            format_expression_for_display("log(sqrt(inv(4)))"),
            "log(√(x⁻¹(4)))",
        )

    def test_display_formatting_does_not_affect_engine_input(self) -> None:
        """The engine must keep receiving the canonical token, never the symbol."""
        state = CalculatorState(engine=CalculationEngine())
        state.press("sqrt(")
        state.press("4")
        state.press(")")
        self.assertEqual(state.expression, "sqrt(4)")
        self.assertEqual(format_expression_for_display(state.expression), "√(4)")

        result = state.evaluate()
        self.assertTrue(result.ok)
        self.assertEqual(result.value, 2.0)


if __name__ == "__main__":
    unittest.main()
