import unittest
from unittest import mock

from software.audio_only import AudioOnlyCalculator
from software.ui.shared.error_messages import ERROR_MESSAGES


class AudioOnlyCalculatorTest(unittest.TestCase):
    """RF-04: with no usable video the calculator still answers by voice."""

    def setUp(self) -> None:
        self.speech = mock.MagicMock()
        self.calc = AudioOnlyCalculator(speech=self.speech)

    def _spoken(self) -> list[str]:
        return [call.args[0] for call in self.speech.interrupt_and_say.call_args_list]

    def test_announces_the_result_of_an_expression(self) -> None:
        with mock.patch("builtins.print"):
            self.calc.submit("2+3*4")
        self.assertEqual(self._spoken(), ["Resultado 14"])

    def test_announces_domain_errors_with_the_prd_code_and_priority(self) -> None:
        with mock.patch("builtins.print"):
            self.calc.submit("1/0")
        spoken = self._spoken()[0]
        self.assertTrue(spoken.startswith("Erro 001."))
        self.assertIn(ERROR_MESSAGES["ERR-001"], spoken)

    def test_each_submission_starts_from_a_clean_expression(self) -> None:
        with mock.patch("builtins.print"):
            self.calc.submit("2+2")
            self.calc.submit("3+3")
        self.assertEqual(self._spoken(), ["Resultado 4", "Resultado 6"])

    def test_never_requires_a_visual_surface(self) -> None:
        """The audio path must not import a Tk front to work."""
        import software.audio_only as audio_only

        with open(audio_only.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("ttkbootstrap", source)
        self.assertNotIn("tkinter", source)


if __name__ == "__main__":
    unittest.main()
