import unittest

from software.core import CalculationEngine, CalculatorState


class RecallLastAnswerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state = CalculatorState(engine=CalculationEngine())

    def test_recall_without_previous_result_behaves_like_wrn_010(self) -> None:
        result = self.state.recall_last_answer()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "WRN-010")
        self.assertEqual(result.priority, "P2")

    def test_recall_returns_the_last_complete_result(self) -> None:
        self.state.expression = "10+4"
        self.state.evaluate()

        result = self.state.recall_last_answer()

        self.assertTrue(result.ok)
        self.assertEqual(result.display, "14")
        self.assertEqual(result.value, 14.0)

    def test_recall_does_not_recalculate_or_touch_the_expression(self) -> None:
        self.state.expression = "10+4"
        self.state.evaluate()
        # O usuário começa a digitar uma nova expressão...
        self.state.expression = "2+"

        result = self.state.recall_last_answer()

        # ...e o recall não deve mexer nela nem produzir um novo resultado.
        self.assertEqual(self.state.expression, "2+")
        self.assertEqual(result.display, "14")
        self.assertEqual(len(self.state.history), 1)  # nenhuma nova entrada no histórico

    def test_recall_returns_untruncated_value_even_for_long_results(self) -> None:
        self.state.expression = "1/3"
        self.state.evaluate()

        result = self.state.recall_last_answer()

        # O valor completo (sem qualquer truncamento de exibição) deve estar disponível.
        self.assertEqual(result.display, self.state.last_result.display)
        self.assertGreater(len(result.display), 1)


if __name__ == "__main__":
    unittest.main()
