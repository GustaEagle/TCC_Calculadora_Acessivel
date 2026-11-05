"""RF-05: physical keypad presses drive both fronts like the PC keyboard does.

Builds the real Tk fronts (Xvfb in the CI, like test_history_via_keyboard.py)
with a fake matrix keyboard, and feeds events through the same pump the
scanner thread uses. The point is the Ctrl/Shift functions: from the matrix,
every key carries its full catalogue entry, not just the primary token.
"""

import contextlib
import unittest
from unittest import mock

from software.hw_platform.keypad_matrix import KeyEvent
from software.hw_platform.keypad_pinout import SWITCHES
from software.ui.shared.keypad import (
    HELP_CANCELLED_SPEECH,
    HELP_PROMPT_SPEECH,
    NO_FUNCTION_SPEECH,
    entry_for_keycap,
    key_description,
    spoken_token,
)


def _load(front: str):
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


class FakeKeyboard:
    def __init__(self) -> None:
        self.sink = None

    def attach(self, sink) -> None:
        self.sink = sink

    def detach(self) -> None:
        self.sink = None


def press(app, keyboard: FakeKeyboard, *keycaps: str) -> None:
    for keycap in keycaps:
        sw = next(sw for sw in SWITCHES if sw.keycap == keycap)
        keyboard.sink(KeyEvent(keycap, sw.coord, sw.switch, True, 0, 0, 0.0))
        keyboard.sink(KeyEvent(keycap, sw.coord, sw.switch, False, 0, 0, 0.0))
    app.matrix_input.tick()


class MatrixKeysInFrontsTest(unittest.TestCase):
    FRONTS = ("lcd", "hdmi")

    @contextlib.contextmanager
    def front(self, name: str):
        """One front at a time: ttkbootstrap cannot hold two live windows."""
        keyboard = FakeKeyboard()
        app = _load(name)(keypad_matrix=keyboard)
        app.speech = mock.MagicMock()
        app.matrix_input.start()
        try:
            yield app, keyboard
        finally:
            app.root.destroy()

    def test_digits_and_operators_reach_the_expression(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "+", "2")
                self.assertEqual(app.state.expression, "7+2")

    def test_ctrl_then_sen_inserts_arc_sine(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "Ctrl", "sen")
                self.assertEqual(app.state.expression, "asin(")
                self.assertFalse(app.ctrl_active, "o Ctrl tem de ser consumido")

    # O modificador Shift está no keycap "exp" desde que exp( foi para o Ctrl
    # da tecla "e" (ver _KEYCAP_TO_LABEL). O keycap "Shift" passou a ser o
    # "DR" (graus/radianos), por isso estes testes pressionam "exp".
    def test_shift_then_log_inserts_log_in_base(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "exp", "log")
                self.assertEqual(app.state.expression, "logbase(")

    def test_shift_then_slash_toggles_the_angle_mode(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "exp", "/")
                self.assertEqual(app.state.angle_mode, "rad")
                # Indicador e voz acompanham o modo: quem não vê a tela só tem a voz.
                self.assertEqual(app.mode_var.get(), "RAD")
                app.speech.interrupt_and_say.assert_called_with("Modo rad")
                self.assertEqual(app.state.expression, "")
                self.assertFalse(app.shift_active, "o Shift tem de ser consumido")

    def test_ctrl_plus_and_minus_change_volume_without_typing(self) -> None:
        from software.accessibility.speech import SpeechService

        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                app.volume = mock.MagicMock()
                app.volume.increase.return_value = 70
                app.volume.decrease.return_value = 60

                press(app, keyboard, "Ctrl", "+")
                app.volume.increase.assert_called_once()
                self.assertEqual(app.state.expression, "", "Ctrl + '+' não digita operador")
                app.speech.interrupt_and_say.assert_called_with(
                    "Volume 70 por cento", priority=SpeechService.CONFIG
                )
                self.assertFalse(app.ctrl_active, "o Ctrl tem de ser consumido")

                press(app, keyboard, "Ctrl", "-")
                app.volume.decrease.assert_called_once()
                self.assertEqual(app.state.expression, "", "Ctrl + '-' não digita operador")

    def test_plus_and_minus_without_ctrl_stay_operators(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                app.volume = mock.MagicMock()
                press(app, keyboard, "7", "+", "2", "-", "1")
                self.assertEqual(app.state.expression, "7+2-1")
                app.volume.increase.assert_not_called()
                app.volume.decrease.assert_not_called()

    def test_question_mark_arms_the_lookup_mode(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "?")
                self.assertTrue(app.help_active)
                app.speech.interrupt_and_say.assert_called_with(HELP_PROMPT_SPEECH)
                self.assertEqual(app.state.expression, "")

    def test_the_next_key_is_described_and_not_inserted(self) -> None:
        """O defeito relatado em bancada: a tecla seguinte entrava na
        expressão. Agora ela é DESCRITA e a expressão fica intacta."""
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "?", "log")
                self.assertEqual(app.state.expression, "7")
                app.speech.interrupt_and_say.assert_called_with(
                    key_description(*entry_for_keycap("log"))
                )
                self.assertFalse(app.help_active, "o modo é de um só uso")

    def test_a_digit_after_the_question_mark_is_described_not_typed(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "?", "7")
                self.assertEqual(app.state.expression, "")
                app.speech.interrupt_and_say.assert_called_with(
                    key_description(*entry_for_keycap("7"))
                )

    def test_a_second_question_mark_cancels_the_mode(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "?", "?")
                self.assertFalse(app.help_active)
                app.speech.interrupt_and_say.assert_called_with(HELP_CANCELLED_SPEECH)
                press(app, keyboard, "7")
                self.assertEqual(app.state.expression, "7", "cancelado, o 7 entra")

    def test_the_mode_is_one_shot(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "?", "7", "8")
                self.assertEqual(app.state.expression, "8", "só o 7 foi consultado")

    def test_describing_a_modifier_does_not_arm_it(self) -> None:
        """"?" seguido de Ctrl descreve o Ctrl em vez de o ligar."""
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "?", "Ctrl")
                self.assertFalse(app.ctrl_active)
                self.assertFalse(app.help_active)

    def test_lookup_touches_no_state(self) -> None:
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                app.volume = mock.MagicMock()
                press(app, keyboard, "5", "nCr", "2", "=")
                result_before = app.result_var.get()
                ans_before = app.state.ans
                press(app, keyboard, "?", "Shift")
                self.assertEqual(app.result_var.get(), result_before)
                self.assertEqual(app.state.ans, ans_before)
                self.assertEqual(app.state.angle_mode, "deg")
                app.volume.increase.assert_not_called()

    def test_the_description_is_the_same_in_both_fronts(self) -> None:
        """RF-04/RF-10: paridade entre fronts."""
        spoken = []
        for name in self.FRONTS:
            with self.front(name) as (app, keyboard):
                press(app, keyboard, "?", "Ans")
                spoken.append(app.speech.interrupt_and_say.call_args.args[0])
        self.assertEqual(len(set(spoken)), 1, msg=f"descrição divergente: {spoken}")

    def test_unknown_keycaps_still_announce_no_function(self) -> None:
        """O caminho de tecla não mapeada continua a existir para teclas
        genuinamente desconhecidas (keycap fora do mapa, defeito de hardware)."""
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, _keyboard):
                app._on_unmapped_key(
                    KeyEvent("ZZZ", "C0L0", 0, True, 0, 0, 0.0)
                )
                app.speech.interrupt_and_say.assert_called_with(NO_FUNCTION_SPEECH)

    def test_every_key_interrupts_the_previous_key_instead_of_queueing(self) -> None:
        # RF-08 (nova regra): cada tecla corta a fala da anterior e anuncia só a
        # si mesma. Em digitação rápida não há fila acumulada - por isso o
        # feedback de tecla sai por interrupt_and_say, nunca por say.
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "8", "9")
                spoken = [c.args[0] for c in app.speech.interrupt_and_say.call_args_list]
                self.assertEqual(
                    spoken,
                    [spoken_token("7"), spoken_token("8"), spoken_token("9")],
                )
                app.speech.say.assert_not_called()

    def test_operator_replacement_speaks_substituindo_then_the_operator(self) -> None:
        # Substituir um operador por outro ("7+" e depois "-"): o mesmo toque fala
        # "Substituindo" (cortando a tecla anterior) e, logo atrás na fila, o nome
        # do novo operador - a troca não se corta a si mesma, mas a PRÓXIMA tecla
        # ainda corta as duas.
        for name in self.FRONTS:
            with self.subTest(front=name), self.front(name) as (app, keyboard):
                press(app, keyboard, "7", "+", "-")
                self.assertEqual(app.state.expression, "7-")
                # A 1ª fala do toque de "-" corta a fala anterior: é "Substituindo".
                interrupted = [c.args[0] for c in app.speech.interrupt_and_say.call_args_list]
                self.assertEqual(interrupted, ["7", spoken_token("+"), "Substituindo"])
                # O nome do operador entra em fila ATRÁS do "Substituindo".
                queued = [c.args[0] for c in app.speech.say.call_args_list]
                self.assertEqual(queued, [spoken_token("-")])

    def test_typing_key_closes_history_then_announces_the_key(self) -> None:
        # Preservação: digitar com o histórico aberto (LCD) fecha-o e ainda
        # anuncia a tecla. "Histórico fechado" é a 1ª fala do toque (corta a
        # leitura do histórico); o nome da tecla entra em fila atrás dela.
        with self.front("lcd") as (app, keyboard):
            press(app, keyboard, "Ctrl", "Ans")  # abre o histórico
            self.assertTrue(app.history_open)
            app.speech.reset_mock()

            press(app, keyboard, "5")
            self.assertFalse(app.history_open)
            interrupted = [c.args[0] for c in app.speech.interrupt_and_say.call_args_list]
            queued = [c.args[0] for c in app.speech.say.call_args_list]
            self.assertEqual(interrupted, ["Histórico fechado"])
            self.assertEqual(queued, [spoken_token("5")])

    def test_run_stops_the_pump_when_the_window_closes(self) -> None:
        keyboard = FakeKeyboard()
        app = _load("lcd")(keypad_matrix=keyboard)
        app.speech = mock.MagicMock()
        app.root.after(50, app.root.destroy)
        app.run()
        self.assertIsNone(keyboard.sink, "a janela fechou mas o front ficou ligado à matriz")

    def test_front_without_matrix_has_no_pump(self) -> None:
        app = _load("lcd")()
        app.speech = mock.MagicMock()
        try:
            self.assertIsNone(app.matrix_input)
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
