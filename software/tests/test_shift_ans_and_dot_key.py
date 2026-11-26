"""Shift + Ans (ler a expressão) e o mapeamento da tecla "." (decimal/vírgula).

Constrói os fronts Tk reais (Xvfb no CI, como test_matrix_keys_in_fronts.py),
com a voz trocada por um mock, e exercita o mesmo _handle_token que o teclado
físico e o de PC usam. O ponto é o comportamento integrado: o que é falado, o
que entra (ou não) na expressão e o modo angular efetivo (DEG/RAD no Shift+"/").
"""

import math
import unittest
from unittest import mock

from software.core.engine import CalculationEngine
from software.ui.shared.keypad import LEFT_BUTTONS, entry_for_keycap

FRONTS = ("lcd", "hdmi")


def _load(front: str):
    module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
    return module.CalculatorApp


def _spoken(app) -> list[str]:
    return [call.args[0] for call in app.speech.interrupt_and_say.call_args_list]


class ShiftAnsReadsCurrentExpressionTest(unittest.TestCase):
    """§1: Shift + Ans lê a expressão da linha de cálculo, sem calcular."""

    def _press_shift_then_ans(self, app) -> None:
        """Como chega do teclado de PC: sem 'shifted' (o front o injeta)."""
        app._handle_token("Shift", None, None)
        app._handle_token("Ans", None, None)

    def test_reads_the_current_incomplete_expression(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    for token in ("3", "-", "2", "+"):
                        app._handle_token(token, None, None)
                    app.speech.reset_mock()

                    self._press_shift_then_ans(app)

                    self.assertIn("3 menos 2 mais", _spoken(app))
                    # Não avalia nem altera a linha de cálculo.
                    self.assertEqual(app.state.expression, "3-2+")
                    self.assertIsNone(app.state.last_result)
                    self.assertEqual(app.state.history, [])
                finally:
                    app.root.destroy()

    def test_empty_line_is_handled_safely(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    self._press_shift_then_ans(app)  # linha vazia: não pode lançar
                    self.assertIn("Expressão vazia", _spoken(app))
                    self.assertEqual(app.state.expression, "")
                finally:
                    app.root.destroy()

    def test_ans_alone_still_inserts_the_previous_answer(self) -> None:
        """Sem Shift, Ans continua sendo Ans - a leitura não sequestra a tecla."""
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    app._handle_token("Ans", None, None)
                    self.assertEqual(app.state.expression, "Ans")
                finally:
                    app.root.destroy()

    def test_reading_does_not_come_from_history(self) -> None:
        """A fonte é a linha atual, nunca o histórico: lê o que foi digitado."""
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    # Um cálculo vai para o histórico...
                    for token in ("9", "+", "9", "="):
                        app._handle_token(token, None, None)
                    # ...e o usuário começa uma expressão nova.
                    app._handle_token("AC", None, None)
                    for token in ("5", "+", "4"):
                        app._handle_token(token, None, None)
                    app.speech.reset_mock()

                    self._press_shift_then_ans(app)

                    falado = _spoken(app)
                    self.assertIn("5 mais 4", falado)
                    self.assertNotIn("Histórico", " ".join(falado))
                finally:
                    app.root.destroy()


class DotKeyMappingTest(unittest.TestCase):
    """A tecla "." (keycap "," da matriz): ponto decimal no principal, vírgula no Shift.

    Usa a entrada do catálogo da tecla física (entry_for_keycap) para provar
    que é o mapeamento real que dirige o comportamento. A alternância DEG/RAD
    fica no Shift + "/", não nesta tecla.
    """

    def setUp(self) -> None:
        self.entry = entry_for_keycap(",")  # (primary, ctrl, shift) da tecla

    def test_the_catalogue_entry_matches_the_mapping(self) -> None:
        self.assertEqual(self.entry, (".", None, ","))

    def test_primary_press_inserts_a_decimal_point(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    for token in ("1", "2"):
                        app._handle_token(token, None, None)
                    app._handle_token(*self.entry)  # "." -> ponto decimal
                    app._handle_token("5", None, None)

                    self.assertEqual(app.state.expression, "12.5")
                    # A tecla não mexe no modo angular.
                    self.assertEqual(app.state.angle_mode, "deg")
                finally:
                    app.root.destroy()

    def test_shift_inserts_a_comma(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    # A vírgula serve às funções genuinamente BINÁRIAS. O nCr
                    # já não é uma delas (passou a infixo, sem parênteses nem
                    # vírgula); as conversões de coordenadas continuam a ser.
                    app._handle_token("polar(", None, None)
                    app._handle_token("5", None, None)
                    app._handle_token("Shift", None, None)
                    app._handle_token(*self.entry)  # Shift + "." -> vírgula
                    app._handle_token("2", None, None)
                    app._handle_token(")", None, None)

                    self.assertEqual(app.state.expression, "polar(5,2)")
                finally:
                    app.root.destroy()


class SlashKeyTogglesAngleModeTest(unittest.TestCase):
    """DEG/RAD continua em Shift + "/" (atalho original, preservado)."""

    def test_shift_slash_toggles_the_angle_mode(self) -> None:
        entry = entry_for_keycap("/")  # ("/", None, "RAD/DEG")
        self.assertEqual(entry, ("/", None, "RAD/DEG"))
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    app._handle_token("Shift", None, None)
                    app._handle_token(*entry)  # Shift + "/" -> alterna o modo
                    self.assertEqual(app.state.angle_mode, "rad")
                    self.assertEqual(app.mode_var.get(), "RAD")
                    self.assertEqual(app.state.engine.angle_mode, "rad")
                    self.assertEqual(app.state.expression, "")
                finally:
                    app.root.destroy()


class ModifierRowRotationTest(unittest.TestCase):
    """Rotação dos modificadores da linha L5.

    exp( saiu da linha e foi para o Ctrl da tecla "e" (Euler). Isso libertou o
    keycap "exp", que assumiu o Shift, e empurrou o keycap "Shift" para o "DR"
    (graus/radianos). Os keycaps impressos ficam desalinhados com a função e
    têm de ser trocados de posição no hotswap.
    """

    def test_exp_keycap_is_now_the_shift_modifier(self) -> None:
        self.assertEqual(entry_for_keycap("exp"), ("Shift", None, None))

    def test_shift_keycap_is_now_the_angle_mode_toggle(self) -> None:
        self.assertEqual(entry_for_keycap("Shift"), ("RAD/DEG", None, None))

    def test_ctrl_keycap_is_untouched(self) -> None:
        self.assertEqual(entry_for_keycap("Ctrl"), ("Ctrl", None, None))

    def test_the_exponential_left_the_modifier_row(self) -> None:
        """Nenhum dos três modificadores carrega exp( em função secundária."""
        for keycap in ("Ctrl", "exp", "Shift"):
            with self.subTest(keycap=keycap):
                self.assertNotIn("exp(", entry_for_keycap(keycap))

    def test_physical_order_now_matches_the_on_screen_order(self) -> None:
        """A linha L5 entrega Ctrl, Shift, DR - a mesma ordem dos botões."""
        labels = [item[0] for item in LEFT_BUTTONS[-1]]
        self.assertEqual(labels, ["Ctrl", "Shift", "DR"])
        physical = [entry_for_keycap(kc)[0] for kc in ("Ctrl", "exp", "Shift")]
        self.assertEqual(physical, ["Ctrl", "Shift", "RAD/DEG"])

    def test_angle_toggle_from_the_shift_keycap(self) -> None:
        entry = entry_for_keycap("Shift")
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    self.assertEqual(app.state.angle_mode, "deg")

                    app._handle_token(*entry)  # 1º acionamento
                    self.assertEqual(app.state.angle_mode, "rad")
                    self.assertEqual(app.mode_var.get(), "RAD")
                    self.assertEqual(app.state.engine.angle_mode, "rad")

                    app._handle_token(*entry)  # 2º acionamento
                    self.assertEqual(app.state.angle_mode, "deg")
                    self.assertEqual(app.mode_var.get(), "DEG")

                    # Alternar o modo não digita nada na expressão.
                    self.assertEqual(app.state.expression, "")
                finally:
                    app.root.destroy()

    def test_exp_keycap_activates_the_shift_state(self) -> None:
        """O keycap "exp" tem de ligar o Shift de verdade: pressioná-lo e
        depois "." dá a vírgula, que é função de Shift do ponto."""
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    app._handle_token(*entry_for_keycap("exp"))
                    app._handle_token(*entry_for_keycap(","))  # Shift + "." -> ","
                    self.assertEqual(app.state.expression, ",")
                    self.assertEqual(app.state.angle_mode, "deg")
                finally:
                    app.root.destroy()


class EulerKeyCarriesTheExpKeyTest(unittest.TestCase):
    """exp( é a função de Ctrl da tecla "e".

    A tecla EXP é entrada de expoente de base DEZ (3 EXP 8 = 3x10^8), não a
    exponencial de base e - essa continua acessível por "e ^ x", na primária
    desta mesma tecla. O realojamento foi o que libertou o keycap "exp" para
    assumir o Shift (ver ModifierRowRotationTest).
    """

    def setUp(self) -> None:
        self.entry = entry_for_keycap("e")  # (primary, ctrl, shift)

    def test_the_catalogue_entry_matches_the_mapping(self) -> None:
        self.assertEqual(self.entry, ("e", "exp(", None))

    def test_primary_press_still_inserts_the_constant(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    app._handle_token(*self.entry)
                    self.assertEqual(app.state.expression, "e")
                finally:
                    app.root.destroy()

    def test_ctrl_inserts_the_exp_token(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front):
                app = _load(front)()
                app.speech = mock.MagicMock()
                try:
                    app._handle_token("Ctrl", None, None)
                    app._handle_token(*self.entry)  # Ctrl + e -> exp(
                    app._handle_token("2", None, None)

                    self.assertEqual(app.state.expression, "exp(2")
                    self.assertEqual(app.state.angle_mode, "deg", "Ctrl não pode alternar o modo")
                finally:
                    app.root.destroy()

    def test_exp_is_a_power_of_ten(self) -> None:
        """2 x exp(2) = 200, não 14,78: EXP é expoente de base dez."""
        engine = CalculationEngine()
        self.assertEqual(engine.evaluate("2*exp(2)").display, "200")
        self.assertEqual(engine.evaluate("3exp(8)").display, "300000000")
        self.assertEqual(engine.evaluate("exp(0)").display, "1")

    def test_the_euler_exponential_is_still_reachable(self) -> None:
        """e^x não se perdeu: é a primária desta tecla com o operador ^."""
        engine = CalculationEngine()
        self.assertAlmostEqual(engine.evaluate("e^1").value, math.e)
        self.assertAlmostEqual(engine.evaluate("e^2").value, math.e**2)


if __name__ == "__main__":
    unittest.main()
