import unittest

from software.core import CalculatorState
from software.ui.shared.history import recent_entries, spoken_history


def _run(state: CalculatorState, expression: str) -> None:
    state.press("AC")
    for char in expression:
        state.press(char)
    state.press("=")


class RecentEntriesTest(unittest.TestCase):
    """CalculatorState guarda erros no histórico; a UI não deve mostrá-los."""

    def test_failed_operations_are_left_out(self) -> None:
        state = CalculatorState()
        _run(state, "2+2")
        _run(state, "1/0")   # ERR-001
        _run(state, "3*3")

        entries = recent_entries(state.history, 10)
        displays = [e.display for e in entries]
        self.assertEqual(displays, ["9", "4"], "erro vazou para o histórico")
        self.assertTrue(all(e.ok for e in entries))

    def test_newest_first(self) -> None:
        state = CalculatorState()
        _run(state, "1+1")
        _run(state, "2+2")
        self.assertEqual([e.display for e in recent_entries(state.history, 10)], ["4", "2"])

    def test_limit_is_respected(self) -> None:
        state = CalculatorState()
        for i in range(1, 6):
            _run(state, f"{i}+0")
        self.assertEqual(len(recent_entries(state.history, 3)), 3)

    def test_history_with_only_errors_reads_as_empty(self) -> None:
        state = CalculatorState()
        _run(state, "1/0")
        self.assertEqual(recent_entries(state.history, 10), [])


class SpokenHistoryTest(unittest.TestCase):
    def test_empty_history_is_announced_clearly(self) -> None:
        self.assertIn("vazio", spoken_history([]).lower())

    def test_entries_are_announced_with_expression_and_value(self) -> None:
        state = CalculatorState()
        _run(state, "2+2")
        frase = spoken_history(recent_entries(state.history, 10))
        self.assertIn("2+2", frase)
        self.assertIn("igual a 4", frase)

    def test_error_codes_are_never_spoken_as_a_result(self) -> None:
        state = CalculatorState()
        _run(state, "1/0")
        _run(state, "5+5")
        frase = spoken_history(recent_entries(state.history, 10))
        self.assertNotIn("ERR-", frase)


if __name__ == "__main__":
    unittest.main()
