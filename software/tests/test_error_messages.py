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
            # nCr/nPr são INFIXOS (BREAKING): nCr(2, 5) daria ERR-007.
            "ERR-004": "2 nCr 5",
            "ERR-005": "(-1)!",
            "ERR-007": "2+*2",
            "ERR-008": "",
            # ERR-009 estava no catálogo §13 e nunca era emitido pelo motor.
            "ERR-009": "polar(1, 2, 3)",
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

    def test_err_008_is_p2_and_spoken_as_aviso(self) -> None:
        """§13: o ERR-008 é ERR-xxx mas P2 - a tabela manda «Aviso 008».
        O prefixo do código não decide a prioridade sozinho."""
        self.assertEqual(spoken_priority_prefix("ERR-008"), "Aviso")

    def test_every_code_prefix_matches_the_engine_priority(self) -> None:
        """O prefixo falado tem de concordar com a prioridade que o motor
        atribui ao resultado - mesmo código, mesmo significado (RF-07)."""
        engine = CalculationEngine()
        for expression in ("1/0", "2+*2", "", "polar(5", "polar(1, 2, 3)"):
            with self.subTest(expression=expression):
                result = engine.evaluate(expression)
                expected = "Erro" if result.priority == "P1" else "Aviso"
                self.assertEqual(spoken_priority_prefix(result.code), expected)

    def test_friendly_message_falls_back_to_engine_message_when_unmapped(self) -> None:
        self.assertEqual(friendly_message("ERR-999", "mensagem crua"), "mensagem crua")

    def test_friendly_message_prefers_mapped_text(self) -> None:
        self.assertEqual(friendly_message("ERR-001", "mensagem crua"), ERROR_MESSAGES["ERR-001"])


if __name__ == "__main__":
    unittest.main()
