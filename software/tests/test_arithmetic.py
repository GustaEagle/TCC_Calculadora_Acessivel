import unittest
import math
from software.core import CalculationEngine

class ArithmeticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine(angle_mode="deg")

    def test_basic_operations(self) -> None:
        # Soma
        self.assertEqual(self.engine.evaluate("10+5").value, 15)
        # Subtração
        self.assertEqual(self.engine.evaluate("20-8").value, 12)
        # Multiplicação
        self.assertEqual(self.engine.evaluate("6*7").value, 42)
        self.assertEqual(self.engine.evaluate("6×7").value, 42)
        # Divisão
        self.assertEqual(self.engine.evaluate("100/4").value, 25)
        self.assertEqual(self.engine.evaluate("100÷4").value, 25)

    def test_algebraic_operations(self) -> None:
        # Potenciação
        self.assertEqual(self.engine.evaluate("2^3").value, 8)
        self.assertEqual(self.engine.evaluate("2**3").value, 8)
        # Radiciação
        self.assertEqual(self.engine.evaluate("√64").value, 8)
        self.assertEqual(self.engine.evaluate("sqrt(81)").value, 9)
        # Porcentagem
        self.assertEqual(self.engine.evaluate("50%").value, 0.5)
        self.assertEqual(self.engine.evaluate("10+50%").value, 10.5)

    def test_numbers_and_precedence(self) -> None:
        # Números negativos
        self.assertEqual(self.engine.evaluate("-5+3").value, -2)
        self.assertEqual(self.engine.evaluate("10*(-2)").value, -20)
        # Casas decimais
        self.assertAlmostEqual(self.engine.evaluate("1.5+2.75").value, 4.25)
        # Prioridade de operadores
        self.assertEqual(self.engine.evaluate("2+3*4").value, 14)
        # Parênteses
        self.assertEqual(self.engine.evaluate("(2+3)*4").value, 20)

    def test_logarithms(self) -> None:
        # Logaritmo decimal (log)
        self.assertAlmostEqual(self.engine.evaluate("log(100)").value, 2)
        # Logaritmo natural (ln)
        self.assertAlmostEqual(self.engine.evaluate("ln(e)").value, 1)
        # Logaritmo em bases variáveis (logbase(base, value))
        self.assertAlmostEqual(self.engine.evaluate("logbase(2, 8)").value, 3)
        self.assertAlmostEqual(self.engine.evaluate("logbase(5, 125)").value, 3)

    def test_trigonometry(self) -> None:
        # Seno (sin)
        self.assertAlmostEqual(self.engine.evaluate("sin(30)").value, 0.5)
        self.assertAlmostEqual(self.engine.evaluate("sen(30)").value, 0.5)
        # Cosseno (cos)
        self.assertAlmostEqual(self.engine.evaluate("cos(60)").value, 0.5)
        # Tangente (tan)
        self.assertAlmostEqual(self.engine.evaluate("tan(45)").value, 1.0)

    def test_inverse_trigonometry(self) -> None:
        # Inversas
        self.assertAlmostEqual(self.engine.evaluate("sen-1(0.5)").value, 30)
        self.assertAlmostEqual(self.engine.evaluate("cos-1(0.5)").value, 60)
        self.assertAlmostEqual(self.engine.evaluate("tan-1(1)").value, 45)

    def test_errors_and_limits(self) -> None:
        # Divisão por zero
        result = self.engine.evaluate("10/0")
        self.assertEqual(result.code, "ERR-001")
        # Argumento inválido (log de negativo)
        result = self.engine.evaluate("log(-1)")
        self.assertEqual(result.code, "ERR-002")
        # Domínio trigonométrico
        result = self.engine.evaluate("sen-1(2)")
        self.assertEqual(result.code, "ERR-003")
        # Expressão inválida
        result = self.engine.evaluate("2+*2")
        self.assertEqual(result.code, "ERR-007")

    def test_complex_expressions(self) -> None:
        # Identidade trigonométrica: sen(x)^2 + cos(x)^2 = 1
        self.assertAlmostEqual(self.engine.evaluate("sen(30)^2 + cos(30)^2").value, 1.0)
        # Funções aninhadas: log(sqrt(100)) * logbase(2, 64) = 1 * 6 = 6
        self.assertAlmostEqual(self.engine.evaluate("log(sqrt(100)) * logbase(2, 64)").value, 6.0)
        # Álgebra + Log: (10 + 5!) / (log(10) * 2) = 130 / 2 = 65
        self.assertAlmostEqual(self.engine.evaluate("(10 + 5!) / (log(10) * 2)").value, 65.0)
        # Composição: tan(atan(1)) = 1
        self.assertAlmostEqual(self.engine.evaluate("tan(atan(1))").value, 1.0)
        # Porcentagem aninhada: 50% * (100 + 10%) = 0.5 * 100.1 = 50.05
        self.assertAlmostEqual(self.engine.evaluate("50% * (100 + 10%)").value, 50.05)

    def test_stress_parser(self) -> None:
        self.assertEqual(self.engine.evaluate("((((((2+3))))))").value, 5)
        # sin(cos(tan(30)))
        expected = math.sin(math.radians(math.cos(math.radians(math.tan(math.radians(30))))))
        self.assertAlmostEqual(self.engine.evaluate("sin(cos(tan(30)))").value, expected, places=7)
        # (2+3*(4-2^(1+1)))^2 = (2+3*(4-4))^2 = 2^2 = 4
        self.assertEqual(self.engine.evaluate("(2+3*(4-2^(1+1)))^2").value, 4)

    def test_robustness_precision(self) -> None:
        # Precisão e epsilon
        self.assertAlmostEqual(self.engine.evaluate("0.1 + 0.2").value, 0.3, places=9)
        self.assertAlmostEqual(self.engine.evaluate("0.3 - 0.2").value, 0.1, places=9)
        self.assertAlmostEqual(self.engine.evaluate("1 / 3 * 3").value, 1.0, places=9)
        self.assertAlmostEqual(self.engine.evaluate("(0.1 * 10) - 1").value, 0.0, places=9)
        # Cancelamento numérico (limitado pela precisão da float64)
        # 999999.999999 - 999999.999998 = 0.000001
        res = self.engine.evaluate("999999.999999 - 999999.999998")
        self.assertAlmostEqual(res.value, 0.000001, places=9)

    def test_associativity_and_order(self) -> None:
        # Associatividade à esquerda para - e /
        self.assertEqual(self.engine.evaluate("10 - 3 - 2").value, 5)
        self.assertEqual(self.engine.evaluate("100 / 10 / 2").value, 5)
        # 2^3^2: Python (e standard math) é associativo à direita: 2**(3**2) = 512
        self.assertEqual(self.engine.evaluate("2^3^2").value, 512)
        # -3^2: Precedência de potência sobre sinal: -(3**2) = -9
        self.assertEqual(self.engine.evaluate("-3^2").value, -9)

    def test_mathematical_identities(self) -> None:
        # Identidade clássica
        self.assertAlmostEqual(self.engine.evaluate("sin(45)^2 + cos(45)^2").value, 1.0)
        # log(a*b) = log(a) + log(b)
        self.assertAlmostEqual(self.engine.evaluate("log(2*5)").value, self.engine.evaluate("log(2)+log(5)").value)
        # ln(e^x) = x
        self.assertAlmostEqual(self.engine.evaluate("ln(e^5)").value, 5.0)
        # e^(ln(x)) = x
        self.assertAlmostEqual(self.engine.evaluate("e^(ln(10))").value, 10.0)
        # tan(x) = sin(x)/cos(x)
        self.assertAlmostEqual(self.engine.evaluate("tan(30)").value, self.engine.evaluate("sin(30)/cos(30)").value)

    def test_aggressive_errors(self) -> None:
        # Erros de sintaxe/parser
        self.assertEqual(self.engine.evaluate("()").code, "ERR-007")
        self.assertEqual(self.engine.evaluate("(2+3").code, "ERR-007")
        self.assertEqual(self.engine.evaluate("2+").code, "ERR-007")
        self.assertEqual(self.engine.evaluate("sin").code, "ERR-007")
        self.assertEqual(self.engine.evaluate("log()").code, "ERR-007")
        # Erros de domínio
        self.assertEqual(self.engine.evaluate("sqrt(-1)").code, "ERR-002")
        self.assertEqual(self.engine.evaluate("1/0 + 5").code, "ERR-001")

    def test_inverse_consistency(self) -> None:
        self.assertAlmostEqual(self.engine.evaluate("sin(sen-1(0.5))").value, 0.5)
        self.assertAlmostEqual(self.engine.evaluate("cos(cos-1(0.2))").value, 0.2)
        self.assertAlmostEqual(self.engine.evaluate("logbase(10, 10^3)").value, 3.0)
        self.assertAlmostEqual(self.engine.evaluate("e^ln(5)").value, 5.0)

    def test_normalization_ux(self) -> None:
        # Espaços
        self.assertEqual(self.engine.evaluate(" 2 + 2 ").value, 4)
        # UTF-8 e Normalização
        self.assertEqual(self.engine.evaluate("2 × 2").value, 4)
        self.assertEqual(self.engine.evaluate("2 ÷ 2").value, 1)
        # Case insensitive
        self.assertAlmostEqual(self.engine.evaluate("SIN(30)").value, 0.5)
        # 2++2 -> Python trata como 2 + (+2) = 4. PRD não proíbe, mas seremos consistentes.
        self.assertEqual(self.engine.evaluate("2++2").value, 4)

if __name__ == "__main__":
    unittest.main()
