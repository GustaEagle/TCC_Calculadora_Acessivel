"""Tecla "?" como modificador de consulta (spoken-help-key).

A "?" (SW25, C0L4) é um toggle de um só uso, como o Ctrl e o Shift: pressioná-la
e depois qualquer tecla DESCREVE as três funções dessa tecla, sem a executar e
sem tocar na expressão. Pressionar "?" outra vez cancela.

Não é "segurar ? e pressionar": o scanner varre a matriz coluna a coluna e não
identifica duas teclas pressionadas ao mesmo tempo.

Tudo aqui é função pura (sem Tk), para correr em qualquer ambiente; a integração
nos fronts está em test_matrix_keys_in_fronts.py.
"""

from __future__ import annotations

import unittest

from software.hw_platform.keypad_pinout import SWITCHES
from software.hw_platform.keyboard import KeyboardAdapter
from software.ui.shared.keypad import (
    HELP_CANCELLED_SPEECH,
    HELP_PROMPT_SPEECH,
    HELP_TOKEN,
    LEFT_BUTTONS,
    NO_SECONDARY_SPEECH,
    RIGHT_BUTTONS,
    SPOKEN_TOKEN_NAMES,
    entry_for_keycap,
    key_description,
    spoken_token,
)


class HelpKeycapTests(unittest.TestCase):
    def test_question_mark_resolves_to_help_token(self) -> None:
        entry = entry_for_keycap("?")
        self.assertIsNotNone(entry)
        self.assertEqual(entry[0], HELP_TOKEN)

    def test_unknown_keycap_still_has_no_entry(self) -> None:
        self.assertIsNone(entry_for_keycap("ZZZ"))

    def test_no_help_button_on_screen(self) -> None:
        """A consulta é função exclusiva do teclado físico."""
        labels = [label for row in LEFT_BUTTONS + RIGHT_BUTTONS for (label, *_) in row]
        self.assertNotIn("?", labels)

    def test_help_reachable_from_pc_keyboard(self) -> None:
        self.assertEqual(KeyboardAdapter().map_key("?"), HELP_TOKEN)

    def test_the_prompts_are_distinct_and_spoken(self) -> None:
        self.assertTrue(HELP_PROMPT_SPEECH.strip())
        self.assertTrue(HELP_CANCELLED_SPEECH.strip())
        self.assertNotEqual(HELP_PROMPT_SPEECH, HELP_CANCELLED_SPEECH)


class KeyDescriptionTests(unittest.TestCase):
    def test_describes_the_three_layers(self) -> None:
        text = key_description("log(", "ln(", "logbase(")
        self.assertIn("logaritmo decimal", text)
        self.assertIn("logaritmo natural", text)
        self.assertIn("logaritmo na base x", text)

    def test_missing_layers_are_announced_as_none(self) -> None:
        text = key_description("sqrt(", None, None)
        self.assertIn("raiz quadrada", text)
        self.assertEqual(text.count(NO_SECONDARY_SPEECH), 2)

    def test_names_come_from_the_spoken_catalogue(self) -> None:
        """A descrição não pode divergir do que a tecla anuncia em uso real."""
        text = key_description("Ans", "HISTORY", "SPEAK_EXPR")
        for token in ("Ans", "HISTORY", "SPEAK_EXPR"):
            with self.subTest(token=token):
                self.assertIn(spoken_token(token), text)

    def test_every_matrix_key_can_be_described(self) -> None:
        for sw in SWITCHES:
            entry = entry_for_keycap(sw.keycap)
            with self.subTest(keycap=sw.keycap):
                self.assertIsNotNone(entry)
                self.assertTrue(key_description(*entry).strip())

    def test_no_described_token_leaks_a_raw_action_name(self) -> None:
        """Um token de AÇÃO sem nome falado seria lido em inglês. Os dígitos
        ficam de fora de propósito: o motor de voz já os lê como números."""
        leaked = set()
        for sw in SWITCHES:
            for token in entry_for_keycap(sw.keycap):
                if token and not token.isdigit() and token not in SPOKEN_TOKEN_NAMES:
                    leaked.add(token)
        self.assertEqual(leaked, set(), f"tokens sem nome falado: {sorted(leaked)}")


if __name__ == "__main__":
    unittest.main()
