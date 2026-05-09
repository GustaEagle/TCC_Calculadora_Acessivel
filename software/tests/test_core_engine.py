from __future__ import annotations

import unittest

from software.core import CalculationEngine


class CalculationEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()

    def test_basic_arithmetic(self) -> None:
        result = self.engine.evaluate("2+3*4")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "14")

    def test_scientific_functions_use_degrees(self) -> None:
        result = self.engine.evaluate("sen(30)+cos(60)")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "1")

    def test_division_by_zero_error_code(self) -> None:
        result = self.engine.evaluate("1/0")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "ERR-001")

    def test_ans_without_previous_value_warns(self) -> None:
        result = self.engine.evaluate("Ans+1")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "WRN-010")
        self.assertEqual(result.priority, "P2")

    def test_combinatorics(self) -> None:
        result = self.engine.evaluate("nCr(5,2)+nPr(4,2)")
        self.assertTrue(result.ok)
        self.assertEqual(result.display, "22")


if __name__ == "__main__":
    unittest.main()
