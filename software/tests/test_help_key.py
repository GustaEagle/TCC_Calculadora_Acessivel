"""Tecla "?" como ajuda falada (spoken-help-key).

A "?" (SW25, C0L4) existe na PCB e é lida pelo scanner, mas não tinha destino
no software: anunciava só "Tecla sem função". Passa a anunciar o modo angular
e os atalhos do produto - que até aqui não tinham forma de serem descobertos
sem ver a tela ou ler a documentação.

Tudo aqui é função pura (sem Tk), para correr em qualquer ambiente.
"""

from __future__ import annotations

import unittest

from software.hw_platform.keyboard import KeyboardAdapter
from software.ui.shared.keypad import (
    HELP_ENTRIES,
    HELP_TOKEN,
    LEFT_BUTTONS,
    RIGHT_BUTTONS,
    SHORTCUT_TOKENS,
    entry_for_keycap,
    help_covered_tokens,
    help_speech,
)


class HelpKeycapTests(unittest.TestCase):
    def test_question_mark_resolves_to_help_token(self) -> None:
        entry = entry_for_keycap("?")
        self.assertIsNotNone(entry)
        self.assertEqual(entry[0], HELP_TOKEN)

    def test_unknown_keycap_still_has_no_entry(self) -> None:
        """Teclas genuinamente desconhecidas continuam a ser anunciadas como
        sem função - sem retorno, pareceriam avariadas."""
        self.assertIsNone(entry_for_keycap("ZZZ"))

    def test_no_help_button_on_screen(self) -> None:
        """A ajuda é função exclusiva do teclado físico (não-objetivo)."""
        labels = [label for row in LEFT_BUTTONS + RIGHT_BUTTONS for (label, *_) in row]
        self.assertNotIn("?", labels)

    def test_help_reachable_from_pc_keyboard(self) -> None:
        self.assertEqual(KeyboardAdapter().map_key("?"), HELP_TOKEN)


class HelpSpeechContentTests(unittest.TestCase):
    def test_announces_degree_mode(self) -> None:
        text = help_speech("deg")
        self.assertIn("Ajuda", text)
        self.assertIn("graus", text)
        self.assertNotIn("radianos", text)

    def test_announces_radian_mode(self) -> None:
        text = help_speech("rad")
        self.assertIn("radianos", text)

    def test_covers_every_declared_shortcut(self) -> None:
        """Anti-deriva: acrescentar um atalho e esquecer a ajuda tem de falhar
        AQUI, em vez de ficar uma lacuna silenciosa. A comparação é entre
        CONJUNTOS de tokens, não entre textos."""
        self.assertEqual(help_covered_tokens(), frozenset(SHORTCUT_TOKENS))

    def test_every_entry_appears_in_the_speech(self) -> None:
        text = help_speech("deg")
        for description, _combinations, _tokens in HELP_ENTRIES:
            with self.subTest(description=description):
                self.assertIn(description, text)

    def test_keys_are_spoken_by_name_not_by_symbol(self) -> None:
        """Um "+" lido literalmente soaria "mais" no meio de uma frase sobre
        teclas; as combinações usam os nomes de SPOKEN_TOKEN_NAMES."""
        text = help_speech("deg")
        self.assertNotIn("+", text)
        self.assertNotIn("/", text)
        self.assertIn("controle mais resposta anterior", text)

    def test_mode_comes_before_the_shortcuts(self) -> None:
        """A única informação de ESTADO vem primeiro, para quem já conhece a
        ajuda poder cortá-la logo depois (RF-08)."""
        text = help_speech("deg")
        self.assertLess(text.index("graus"), text.index(HELP_ENTRIES[0][0]))


if __name__ == "__main__":
    unittest.main()
