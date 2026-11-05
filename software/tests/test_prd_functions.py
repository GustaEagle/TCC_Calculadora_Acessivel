import unittest
import math
from software.core import CalculationEngine

class PRDFunctionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine(angle_mode="deg")

    def test_trigonometric(self) -> None:
        # Sine
        self.assertAlmostEqual(self.engine.evaluate("sen(30)").value, 0.5)
        self.assertAlmostEqual(self.engine.evaluate("sen-1(0.5)").value, 30)
        
        # Cosine
        self.assertAlmostEqual(self.engine.evaluate("cos(60)").value, 0.5)
        self.assertAlmostEqual(self.engine.evaluate("cos-1(0.5)").value, 60)
        
        # Tangent
        self.assertAlmostEqual(self.engine.evaluate("tan(45)").value, 1.0)
        self.assertAlmostEqual(self.engine.evaluate("tan-1(1)").value, 45)

    def test_logarithmic(self) -> None:
        # Log decimal
        self.assertAlmostEqual(self.engine.evaluate("log(100)").value, 2.0)
        # Log natural
        self.assertAlmostEqual(self.engine.evaluate("ln(e)").value, 1.0)
        # Log custom base (logbase(base, value))
        self.assertAlmostEqual(self.engine.evaluate("logbase(10, 100)").value, 2.0)
        self.assertAlmostEqual(self.engine.evaluate("logbase(2, 8)").value, 3.0)

    def test_constants(self) -> None:
        self.assertAlmostEqual(self.engine.evaluate("π").value, math.pi)
        self.assertAlmostEqual(self.engine.evaluate("e").value, math.e)

    def test_algebraic(self) -> None:
        # Power
        self.assertEqual(self.engine.evaluate("2^3").value, 8)
        # Square root
        self.assertEqual(self.engine.evaluate("sqrt(64)").value, 8)
        self.assertEqual(self.engine.evaluate("√64").value, 8)
        # Factorial
        self.assertEqual(self.engine.evaluate("5!").value, 120)
        # Inverse
        self.assertAlmostEqual(self.engine.evaluate("2^-1").value, 0.5)
        self.assertAlmostEqual(self.engine.evaluate("x^-1", ans=2).value, 0.5)

    def test_combinatorics(self) -> None:
        # Notação INFIXA: a tecla nCr fica ENTRE os operandos (BREAKING).
        # nCr
        self.assertEqual(self.engine.evaluate("10 nCr 3").value, 120)
        # nPr
        self.assertEqual(self.engine.evaluate("10 nPr 3").value, 720)

    def test_conversions(self) -> None:
        # Convenção Casio: o token diz o DESTINO. As duas devolvem AS DUAS
        # componentes - antes só devolviam uma, e no sentido trocado.
        # Pol(x, y) -> (r, ângulo)
        radius, angle = self.engine.evaluate("polar(3, 4)").value
        self.assertAlmostEqual(radius, 5.0)
        self.assertAlmostEqual(angle, 53.13010235415598)

        # Rec(r, ângulo) -> (x, y)
        x_value, y_value = self.engine.evaluate("rect(10, 60)").value
        self.assertAlmostEqual(x_value, 5.0)
        self.assertAlmostEqual(y_value, 8.660254037844387)

    def test_domain_errors(self) -> None:
        # Div by zero
        self.assertEqual(self.engine.evaluate("1/0").code, "ERR-001")
        # Root of negative
        self.assertEqual(self.engine.evaluate("√(-1)").code, "ERR-002")
        # Log of zero
        self.assertEqual(self.engine.evaluate("log(0)").code, "ERR-002")
        # asin out of range
        self.assertEqual(self.engine.evaluate("sen-1(2)").code, "ERR-003")

if __name__ == "__main__":
    unittest.main()
