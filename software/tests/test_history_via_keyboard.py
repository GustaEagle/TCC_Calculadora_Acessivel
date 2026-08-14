"""O atalho do histórico precisa funcionar pela via do TECLADO.

Regressão real: o front HDMI só abria o histórico pelo clique no botão Ans,
porque o teclado chama _handle_token(token, None, None) sem o 'secondary' que
a definição do teclado carrega.
"""

import unittest
from unittest import mock

from software.ui.shared.keypad import HISTORY_TOKEN


def _load(front: str):
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


class HistoryReachableFromKeyboardTest(unittest.TestCase):
    def _press_ctrl_then_ans(self, app) -> None:
        """Como chega do teclado físico: sem 'secondary'."""
        app._handle_token("Ctrl", None, None)
        app._handle_token("Ans", None, None)

    def test_lcd_opens_history_from_the_keyboard(self) -> None:
        app = _load("lcd")()
        app.speech = mock.MagicMock()
        try:
            self._press_ctrl_then_ans(app)
            self.assertTrue(app.history_open, "Ctrl + Ans não abriu o histórico no LCD")
        finally:
            app.root.destroy()

    def test_hdmi_announces_history_from_the_keyboard(self) -> None:
        app = _load("hdmi")()
        app.speech = mock.MagicMock()
        try:
            for token in ("2", "+", "2", "="):
                app._handle_token(token, None, None)
            app.speech.reset_mock()

            self._press_ctrl_then_ans(app)

            spoken = [c.args[0] for c in app.speech.interrupt_and_say.call_args_list]
            self.assertTrue(spoken, "Ctrl + Ans não anunciou nada no HDMI")
            self.assertIn(
                "Histórico", spoken[-1],
                f"Ctrl + Ans no HDMI anunciou outra coisa: {spoken[-1]!r}",
            )
        finally:
            app.root.destroy()

    def test_ans_alone_still_inserts_the_previous_answer(self) -> None:
        """Sem Ctrl, Ans continua sendo Ans - o atalho não pode sequestrar a tecla."""
        app = _load("lcd")()
        app.speech = mock.MagicMock()
        try:
            app._handle_token("Ans", None, None)
            self.assertFalse(app.history_open)
            self.assertEqual(app.state.expression, "Ans")
        finally:
            app.root.destroy()

    def test_history_token_is_not_typed_into_the_expression(self) -> None:
        app = _load("lcd")()
        app.speech = mock.MagicMock()
        try:
            self._press_ctrl_then_ans(app)
            self.assertNotIn(HISTORY_TOKEN, app.state.expression)
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
