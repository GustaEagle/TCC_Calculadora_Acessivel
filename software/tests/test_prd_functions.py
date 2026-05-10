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
        # nCr
        self.assertEqual(self.engine.evaluate("nCr(10, 3)").value, 120)
        # nPr
        self.assertEqual(self.engine.evaluate("nPr(10, 3)").value, 720)

    def test_conversions(self) -> None:
        # Polar -> Rect (x component)
        # polar(radius, angle) -> returns x
        self.assertAlmostEqual(self.engine.evaluate("polar(10, 60)").value, 5.0)
        
        # Rect -> Polar (radius)
        # rect(x, y) -> returns radius
        self.assertAlmostEqual(self.engine.evaluate("rect(3, 4)").value, 5.0)

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
