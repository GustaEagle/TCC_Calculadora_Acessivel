"""Texto falado: decimais, separadores, abertura de parênteses e pronúncia.

Cobre a spec spoken-feedback (T01, T02, T03). Tudo aqui é texto puro, sem Tk e
sem motor de voz: o que importa é o texto ENTREGUE ao TTS.
"""

from __future__ import annotations

import unittest
from unittest import mock

from software.ui.shared import keypad
from software.ui.shared.keypad import (
    LEFT_BUTTONS,
    OPENING_PARENTHESIS_SPEECH,
    RIGHT_BUTTONS,
    SPOKEN_TOKEN_NAMES,
    entry_for_keycap,
    spoken_token,
    tts_text,
)
from software.ui.shared.speech_text import spoken_expression, spoken_number


class DecimalSeparatorTests(unittest.TestCase):
    """T02: "um vírgula dois", com zeros e negativos preservados."""

    def test_spec_examples(self) -> None:
        cases = {
            "1.2": "1 vírgula 2",
            "0.05": "0 vírgula 0 5",
            "-3.5": "menos 3 vírgula 5",
            ".5": "0 vírgula 5",
            "10": "10",
            "-7": "menos 7",
        }
        for number, expected in cases.items():
            with self.subTest(number=number):
                self.assertEqual(spoken_number(number), expected)

    def test_scientific_notation_is_left_alone(self) -> None:
        self.assertEqual(spoken_number("1e+20"), "1e+20")

    def test_decimal_inside_an_expression(self) -> None:
        self.assertEqual(spoken_expression("3.14*2"), "3 vírgula 1 4 vezes 2")


class ArgumentSeparatorTests(unittest.TestCase):
    """Com a vírgula reservada ao decimal, o separador é "ponto e vírgula"."""

    def test_decimal_point_key_is_spoken_as_comma(self) -> None:
        primary, _ctrl, shifted = entry_for_keycap(",")
        self.assertEqual(spoken_token(primary), "vírgula")
        self.assertEqual(spoken_token(shifted), "ponto e vírgula")

    def test_conversion_arguments(self) -> None:
        text = spoken_expression("polar(3,4)")
        self.assertIn("3 ponto e vírgula 4", text)
        self.assertNotIn("3 vírgula 4", text)

    def test_decimal_and_separator_together(self) -> None:
        self.assertIn("1 vírgula 5 ponto e vírgula 2", spoken_expression("polar(1.5,2)"))


class OpeningParenthesisTests(unittest.TestCase):
    """T03: funções com parênteses anunciam a abertura."""

    def test_function_key_feedback(self) -> None:
        primary, _ctrl, _shift = entry_for_keycap("√")
        self.assertEqual(spoken_token(primary), "raiz quadrada, abre parênteses")

    def test_expression_reading(self) -> None:
        self.assertEqual(
            spoken_expression("sqrt(9)"),
            "raiz quadrada, abre parênteses 9 fecha parênteses",
        )

    def test_every_function_token_announces_the_opening(self) -> None:
        suffix = f", {OPENING_PARENTHESIS_SPEECH}"
        for token, name in SPOKEN_TOKEN_NAMES.items():
            with self.subTest(token=token):
                if token.endswith("(") and token != "(":
                    self.assertTrue(name.endswith(suffix), name)
                else:
                    self.assertFalse(name.endswith(suffix), name)

    def test_every_keypad_function_is_covered(self) -> None:
        """Nenhuma tecla insere um token com parênteses sem nome no catálogo."""
        for row in LEFT_BUTTONS + RIGHT_BUTTONS:
            for _label, *tokens in row:
                for token in tokens:
                    if token and token.endswith("(") and token != "(":
                        with self.subTest(token=token):
                            self.assertIn(token, SPOKEN_TOKEN_NAMES)

    def test_plain_parenthesis_is_not_duplicated(self) -> None:
        self.assertEqual(spoken_token("("), "abre parênteses")

    def test_expression_does_not_repeat_the_opening(self) -> None:
        self.assertEqual(spoken_expression("sen(30)").count("abre parênteses"), 1)


class PronunciationDictionaryTests(unittest.TestCase):
    """T01: o texto entregue ao TTS pode diferir do nome do catálogo."""

    def test_starts_empty(self) -> None:
        """Só entra o que a escuta no Pi confirmar como pronúncia."""
        self.assertEqual(keypad.TTS_PRONUNCIATION, {})

    def test_entry_changes_only_what_goes_to_the_voice(self) -> None:
        with mock.patch.dict(keypad.TTS_PRONUNCIATION, {"limpar tudo": "limpá tudo"}):
            self.assertEqual(tts_text("limpar tudo"), "limpá tudo")
            # O catálogo, e logo a tela e a consulta da tecla "?", ficam iguais.
            self.assertEqual(spoken_token("AC"), "limpar tudo")
            labels = [label for row in LEFT_BUTTONS + RIGHT_BUTTONS for (label, *_) in row]
            self.assertIn("AC", labels)

    def test_replacement_is_by_whole_word(self) -> None:
        with mock.patch.dict(keypad.TTS_PRONUNCIATION, {"pi": "pí"}):
            self.assertEqual(tts_text("pi"), "pí")
            self.assertEqual(tts_text("piso"), "piso")

    def test_speech_service_applies_it_before_synthesis(self) -> None:
        from software.accessibility.speech import SpeechService

        class FakeEngine:
            is_ready = True
            failed = False
            sample_rate = 22050

            def __init__(self) -> None:
                self.calls: list[str] = []

            def synthesize(self, text: str) -> bytes:
                self.calls.append(text)
                return b"\x01\x00"

        engine = FakeEngine()
        service = SpeechService(engine=engine, process_factory=lambda text: None)
        with mock.patch.dict(keypad.TTS_PRONUNCIATION, {"limpar tudo": "limpá tudo"}):
            service._produce("limpar tudo")
        self.assertEqual(engine.calls, ["limpá tudo"])


if __name__ == "__main__":
    unittest.main()


class SharedResultSpeechTests(unittest.TestCase):
    """Mesma leitura de resultado no LCD, no monitor e no modo somente áudio."""

    def setUp(self) -> None:
        from software.core.engine import CalculationEngine

        self.engine = CalculationEngine()

    def _audio_only_announcement(self, expression: str) -> str:
        from software.audio_only import AudioOnlyCalculator

        speech = mock.MagicMock()
        calc = AudioOnlyCalculator(speech=speech)
        with mock.patch("builtins.print"):
            calc.announce(self.engine.evaluate(expression))
        return speech.interrupt_and_say.call_args.args[0]

    def test_scalar_in_audio_only(self) -> None:
        self.assertEqual(self._audio_only_announcement("1.2+0"), "Resultado 1 vírgula 2")

    def test_pair_in_audio_only_has_no_tuple_punctuation(self) -> None:
        """O defeito: o modo somente áudio lia "(5, 53.13...)" com a pontuação."""
        text = self._audio_only_announcement("polar(3,4)")
        self.assertEqual(text, "Resultado real 5, ângulo 53 vírgula 1 3 0 1 0 2 3 5")
        self.assertNotIn("(", text)
        self.assertNotIn(")", text)

    def test_audio_only_matches_the_shared_function(self) -> None:
        from software.ui.shared.speech_text import spoken_result

        for expression in ("1.2+0", "polar(3,4)", "rect(2,60)", "2+2"):
            with self.subTest(expression=expression):
                expected = f"Resultado {spoken_result(self.engine.evaluate(expression))}"
                self.assertEqual(self._audio_only_announcement(expression), expected)

    def test_fronts_use_the_shared_function(self) -> None:
        """Nenhum front volta a ter a sua cópia da leitura de resultado."""
        import inspect

        from software.ui.hdmi import app as hdmi_app
        from software.ui.lcd import app as lcd_app

        for module in (lcd_app, hdmi_app):
            with self.subTest(module=module.__name__):
                source = inspect.getsource(module)
                self.assertNotIn("def _spoken_result", source)
                self.assertIn("spoken_result(result)", source)
