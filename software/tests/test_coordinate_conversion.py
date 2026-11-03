"""Conversões polar <-> retangular como operações de PAR (coordinate-conversion).

Antes desta mudança, polar() devolvia só o x e rect() só o raio: a segunda
componente era descartada. O CalculationResult.value já estava tipado para
par e o _format_value já tinha o ramo de tupla - faltava ligar.
"""

from __future__ import annotations

import unittest

from software.core.engine import CalculationEngine
from software.core.models import VALUE_KIND_POLAR, VALUE_KIND_RECTANGULAR


class PolarToRectangularTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def assertPair(self, result, x_value: float, y_value: float) -> None:
        self.assertTrue(result.ok, msg=result.display)
        self.assertIsInstance(result.value, tuple)
        self.assertAlmostEqual(result.value[0], x_value, places=10)
        self.assertAlmostEqual(result.value[1], y_value, places=10)

    def test_conversion_in_degrees(self) -> None:
        result = self.engine.evaluate("polar(2, 60)")
        self.assertPair(result, 1.0, 1.7320508075688772)
        self.assertIn("1.732050808", result.display)

    def test_zero_angle(self) -> None:
        self.assertPair(self.engine.evaluate("polar(1, 0)"), 1.0, 0.0)

    def test_conversion_in_radians(self) -> None:
        engine = CalculationEngine(angle_mode="rad")
        self.assertPair(engine.evaluate("polar(1, 0)"), 1.0, 0.0)

    def test_zero_radius(self) -> None:
        self.assertPair(self.engine.evaluate("polar(0, 45)"), 0.0, 0.0)


class RectangularToPolarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def assertPair(self, result, radius: float, angle: float) -> None:
        self.assertTrue(result.ok, msg=result.display)
        self.assertIsInstance(result.value, tuple)
        self.assertAlmostEqual(result.value[0], radius, places=10)
        self.assertAlmostEqual(result.value[1], angle, places=10)

    def test_canonical_conversion_in_degrees(self) -> None:
        result = self.engine.evaluate("rect(3, 4)")
        self.assertPair(result, 5.0, 53.13010235415598)
        self.assertIn("53.13010235", result.display)

    def test_vertical_axis_without_division_by_zero(self) -> None:
        """atan2 e não atan(y/x): com x = 0 não há divisão por zero."""
        self.assertPair(self.engine.evaluate("rect(0, 1)"), 1.0, 90.0)

    def test_correct_quadrant_for_negative_x(self) -> None:
        result = self.engine.evaluate("rect(-1, 0)")
        self.assertPair(result, 1.0, 180.0)
        self.assertNotAlmostEqual(result.value[1], 0.0, places=6)

    def test_conversion_in_radians(self) -> None:
        engine = CalculationEngine(angle_mode="rad")
        self.assertPair(
            engine.evaluate("rect(1, 1)"), 1.4142135623730951, 0.7853981633974483
        )

    def test_origin(self) -> None:
        self.assertPair(self.engine.evaluate("rect(0, 0)"), 0.0, 0.0)


class PairOnlyAtTopLevelTests(unittest.TestCase):
    """O §5 não define aritmética de pares: uma conversão só é válida como
    expressão COMPLETA. Sem esta guarda sairia um TypeError cru do Python."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_pair_added_to_number(self) -> None:
        self.assertEqual(self.engine.evaluate("polar(2, 60) + 1").code, "ERR-007")

    def test_pair_nested_in_function(self) -> None:
        self.assertEqual(self.engine.evaluate("sqrt(rect(3, 4))").code, "ERR-007")

    def test_pair_as_combinatorics_operand(self) -> None:
        self.assertEqual(self.engine.evaluate("rect(3, 4) nCr 2").code, "ERR-007")

    def test_pair_alone_is_valid(self) -> None:
        result = self.engine.evaluate("rect(3, 4)")
        self.assertTrue(result.ok)
        self.assertIsInstance(result.value, tuple)

    def test_pair_negated(self) -> None:
        self.assertEqual(self.engine.evaluate("-rect(3, 4)").code, "ERR-007")


class ConversionDirectionTests(unittest.TestCase):
    """O sentido vem do nó de TOPO, para o front não reinterpretar a string."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_rectangular_pair_identified(self) -> None:
        self.assertEqual(
            self.engine.evaluate("polar(2, 60)").value_kind, VALUE_KIND_RECTANGULAR
        )

    def test_polar_pair_identified(self) -> None:
        self.assertEqual(self.engine.evaluate("rect(3, 4)").value_kind, VALUE_KIND_POLAR)

    def test_scalar_has_no_conversion_direction(self) -> None:
        self.assertIsNone(self.engine.evaluate("2+2").value_kind)


class ConversionArityTests(unittest.TestCase):
    """ERR-009 estava no PRD §13 e em error_messages.py, mas nunca era emitido."""

    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_polar_with_extra_argument(self) -> None:
        result = self.engine.evaluate("polar(5, 30, 2)")
        self.assertEqual(result.code, "ERR-009")
        self.assertEqual(result.priority, "P1")

    def test_rect_with_extra_argument(self) -> None:
        self.assertEqual(self.engine.evaluate("rect(3, 4, 5)").code, "ERR-009")

    def test_single_argument_is_incomplete_not_invalid(self) -> None:
        result = self.engine.evaluate("polar(5)")
        self.assertEqual(result.code, "ERR-008")
        self.assertEqual(result.priority, "P2")


if __name__ == "__main__":
    unittest.main()
