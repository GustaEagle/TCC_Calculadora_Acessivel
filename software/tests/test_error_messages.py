import unittest

from software.core import CalculationEngine
from software.ui.shared.error_messages import ERROR_MESSAGES, friendly_message, spoken_priority_prefix


class ErrorMessagesTest(unittest.TestCase):
    def test_every_engine_error_code_has_a_friendly_message(self) -> None:
        """Every ERR-xxx/WRN-xxx the engine can raise must map to clear text."""
        engine = CalculationEngine()
        expressions_by_code = {
            "ERR-001": "1/0",
            "ERR-002": "log(-1)",
            "ERR-003": "asin(2)",
            "ERR-004": "nCr(2, 5)",
            "ERR-005": "(-1)!",
            "ERR-007": "2+*2",
            "ERR-008": "",
            "WRN-010": "Ans+1",
        }
        for code, expression in expressions_by_code.items():
            result = engine.evaluate(expression)
            self.assertEqual(result.code, code)
            self.assertIn(code, ERROR_MESSAGES, f"falta mensagem amigável para {code}")

    def test_p1_error_codes_use_erro_prefix(self) -> None:
        self.assertEqual(spoken_priority_prefix("ERR-001"), "Erro")
        self.assertEqual(spoken_priority_prefix("ERR-007"), "Erro")

    def test_p2_warning_codes_use_aviso_prefix(self) -> None:
        self.assertEqual(spoken_priority_prefix("WRN-010"), "Aviso")
        self.assertEqual(spoken_priority_prefix("WRN-020"), "Aviso")

    def test_friendly_message_falls_back_to_engine_message_when_unmapped(self) -> None:
        self.assertEqual(friendly_message("ERR-999", "mensagem crua"), "mensagem crua")

    def test_friendly_message_prefers_mapped_text(self) -> None:
        self.assertEqual(friendly_message("ERR-001", "mensagem crua"), ERROR_MESSAGES["ERR-001"])


if __name__ == "__main__":
    unittest.main()
