"""Bateria de regressão de precedência e associatividade (T07).

Fixa os casos que JÁ estão certos, para que a multiplicação implícita e as
mudanças futuras não os quebrem. Os valores são os de uma calculadora científica
comercial. Ficam de fora os dois casos que dependem do modelo de referência,
ainda por definir: a porcentagem depois de soma (50+10%) e a prioridade da
multiplicação implícita contra a divisão (1/2(3)).
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine

CASES: dict[str, str] = {
    "2+3*4": "14",          # * antes de +
    "10-2*3": "4",
    "2*(3+4)": "14",        # parênteses primeiro
    "2^3^2": "512",         # potência associa à DIREITA: 2^(3^2)
    "2^2^3": "256",
    "-2^2": "-4",           # potência antes do menos unário
    "-(2)^2": "-4",
    "2^-1": "0.5",          # expoente negativo
    "8/2/2": "2",           # divisão associa à esquerda
    "2-3-4": "-5",          # subtração associa à esquerda
    "1/2*3": "1.5",         # * e / da esquerda para a direita
    "3!^2": "36",           # fatorial antes da potência
    "sen(30)^2": "0.25",    # função antes da potência
}


class PrecedenceRegressionTests(unittest.TestCase):
    def test_battery(self) -> None:
        engine = CalculationEngine()
        for expression, expected in CASES.items():
            with self.subTest(expression=expression):
                result = engine.evaluate(expression)
                self.assertTrue(result.ok, msg=result.display)
                self.assertEqual(result.display, expected)


if __name__ == "__main__":
    unittest.main()
