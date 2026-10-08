"""Conversão para texto falado (§1 leitura da expressão, §2 decimais).

Sem display e sem TTS: só a transformação de texto. O que importa é o texto
ENTREGUE ao motor - os dígitos preservados e o "ponto" no lugar certo - já que
é lendo esse texto que o Piper/espeak diz "um ponto dois" em vez de "um dois".
"""

import unittest

from software.ui.shared.speech_text import spoken_expression, spoken_number


class SpokenNumberTest(unittest.TestCase):
    """§2: o separador decimal é falado como "ponto" e os dígitos preservados."""

    def test_examples_from_the_spec(self) -> None:
        casos = {
            "1.2": "1 ponto 2",
            "3.14": "3 ponto 1 4",
            "0.5": "0 ponto 5",
            "-2.75": "menos 2 ponto 7 5",
            "10.05": "10 ponto 0 5",
            "123.456": "123 ponto 4 5 6",
        }
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(spoken_number(valor), esperado)

    def test_integers_and_negatives_are_preserved(self) -> None:
        self.assertEqual(spoken_number("8"), "8")
        self.assertEqual(spoken_number("120"), "120")
        self.assertEqual(spoken_number("-5"), "menos 5")

    def test_intermediate_and_trailing_zeros_survive(self) -> None:
        self.assertEqual(spoken_number("1.0203"), "1 ponto 0 2 0 3")
        self.assertEqual(spoken_number("2.50"), "2 ponto 5 0")

    def test_scientific_notation_is_left_untouched(self) -> None:
        """Não inventar "ponto" onde não há um separador decimal simples."""
        self.assertEqual(spoken_number("1e+20"), "1e+20")
        self.assertEqual(spoken_number("1.5e-07"), "1.5e-07")


class SpokenExpressionTest(unittest.TestCase):
    """§1: a expressão atual é lida preservando ordem e significado."""

    def test_examples_from_the_spec(self) -> None:
        casos = {
            "3-2+": "3 menos 2 mais",
            "5+4": "5 mais 4",
            "8/2": "8 dividido por 2",
            "3*7": "3 vezes 7",
            "2^3": "2 elevado a 3",
            "1.2+3": "1 ponto 2 mais 3",
            "-5+2": "menos 5 mais 2",
        }
        for expr, esperado in casos.items():
            with self.subTest(expr=expr):
                self.assertEqual(spoken_expression(expr), esperado)

    def test_incomplete_expression_is_not_evaluated_just_read(self) -> None:
        self.assertEqual(spoken_expression("3-2+"), "3 menos 2 mais")

    def test_empty_line_is_safe(self) -> None:
        self.assertEqual(spoken_expression(""), "")
        self.assertEqual(spoken_expression("   "), "")

    def test_functions_and_constants_use_the_catalogue_names(self) -> None:
        # O token "sqrt(" já embute o abre-parênteses no nome falado do catálogo.
        self.assertEqual(spoken_expression("sqrt(9)"), "raiz quadrada 9 fecha parênteses")
        self.assertEqual(spoken_expression("2*π"), "2 vezes pi")
        # "logbase(" tem de casar antes de "log(" (casamento pelo token mais longo).
        self.assertIn("logaritmo na base x", spoken_expression("logbase(2,8)"))

    def test_decimal_mixed_with_operators(self) -> None:
        self.assertEqual(spoken_expression("3.14*2"), "3 ponto 1 4 vezes 2")
        self.assertEqual(spoken_expression("-2.75+1"), "menos 2 ponto 7 5 mais 1")
        self.assertEqual(spoken_expression("10.05/5"), "10 ponto 0 5 dividido por 5")


if __name__ == "__main__":
    unittest.main()
