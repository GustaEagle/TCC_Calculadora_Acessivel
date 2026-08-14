import unittest

from software.ui.shared.keypad import (
    KEYPAD_HIDDEN_SPEECH,
    KEYPAD_HIDE_LABEL,
    KEYPAD_SHOW_LABEL,
    KEYPAD_SHOWN_SPEECH,
    keypad_toggle_label,
    keypad_toggle_speech,
)


class KeypadToggleLabelTest(unittest.TestCase):
    """O rótulo descreve a AÇÃO disponível, não o estado atual."""

    def test_hidden_keypad_offers_to_show_it(self) -> None:
        self.assertEqual(keypad_toggle_label(False), KEYPAD_SHOW_LABEL)

    def test_visible_keypad_offers_to_hide_it(self) -> None:
        self.assertEqual(keypad_toggle_label(True), KEYPAD_HIDE_LABEL)

    def test_speech_reports_the_resulting_state(self) -> None:
        self.assertEqual(keypad_toggle_speech(True), KEYPAD_SHOWN_SPEECH)
        self.assertEqual(keypad_toggle_speech(False), KEYPAD_HIDDEN_SPEECH)

    def test_label_stays_short_enough_to_be_discreet(self) -> None:
        """Não pode virar um texto longo que ocupe o rodapé."""
        for label in (KEYPAD_SHOW_LABEL, KEYPAD_HIDE_LABEL):
            self.assertLessEqual(len(label), 20, f"rótulo longo demais: {label!r}")

    def test_labels_are_text_not_only_icons(self) -> None:
        """Discreto não pode significar ilegível/não anunciável."""
        for label in (KEYPAD_SHOW_LABEL, KEYPAD_HIDE_LABEL):
            self.assertTrue(any(c.isalpha() for c in label), f"sem texto: {label!r}")


def _front_source(front: str) -> str:
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "ui" / front / "app.py"
    return path.read_text(encoding="utf-8")


class HdmiKeypadDefaultTest(unittest.TestCase):
    """No monitor o teclado existe, mas começa oculto."""

    def test_hdmi_defaults_to_a_hidden_keypad(self) -> None:
        import ast

        tree = ast.parse(_front_source("hdmi"))
        assigned = [
            node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
            for target in node.targets
            if isinstance(target, ast.Attribute) and target.attr == "controls_visible"
        ]
        self.assertIn(
            False, assigned,
            f"HDMI não inicia com o teclado oculto (achado: {assigned})",
        )

    def test_hdmi_does_not_hard_code_the_toggle_text(self) -> None:
        source = _front_source("hdmi")
        self.assertNotIn("Ocultar Controles", source)
        self.assertNotIn("Exibir Controles", source)


class LcdIsDisplayOnlyTest(unittest.TestCase):
    """O LCD é só a tela: nenhum teclado ou botão desenhado nele."""

    def test_lcd_builds_no_keypad(self) -> None:
        source = _front_source("lcd")
        for marcador in ("LEFT_BUTTONS", "RIGHT_BUTTONS", "_build_buttons", "controls_visible"):
            self.assertNotIn(marcador, source, f"LCD ainda monta teclado ({marcador})")

    def test_lcd_has_no_buttons_at_all(self) -> None:
        source = _front_source("lcd")
        self.assertNotIn("ttk.Button", source, "LCD deveria ser somente display")


if __name__ == "__main__":
    unittest.main()
