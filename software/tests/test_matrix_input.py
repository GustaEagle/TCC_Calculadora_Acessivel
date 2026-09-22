"""RF-05: physical keys reach the front through the same token path as the PC.

Runs without DISPLAY: the pump is exercised with a fake root, like
test_video_watch.py, and the keycap catalogue is plain data.
"""

import unittest

from software.hw_platform.keypad_matrix import KeyEvent
from software.hw_platform.keypad_pinout import SWITCHES
from software.ui.shared.keypad import NO_FUNCTION_SPEECH, entry_for_keycap
from software.ui.shared.matrix_input import MatrixInputPump


class FakeRoot:
    def __init__(self) -> None:
        self.scheduled: list[tuple[int, object]] = []

    def after(self, delay_ms: int, callback) -> None:
        self.scheduled.append((delay_ms, callback))


class FakeKeyboard:
    def __init__(self) -> None:
        self.sink = None

    def attach(self, sink) -> None:
        self.sink = sink

    def detach(self) -> None:
        self.sink = None


def event(keycap: str, pressed: bool = True) -> KeyEvent:
    sw = next(sw for sw in SWITCHES if sw.keycap == keycap)
    return KeyEvent(keycap, sw.coord, sw.switch, pressed, 0, 0, 0.0)


class KeycapCatalogueTest(unittest.TestCase):
    def test_every_switch_but_the_question_mark_has_a_catalogue_entry(self) -> None:
        missing = [sw.keycap for sw in SWITCHES if entry_for_keycap(sw.keycap) is None]
        self.assertEqual(missing, ["?"])
        self.assertEqual(len(SWITCHES) - len(missing), 37)

    def test_secondary_functions_come_with_the_key(self) -> None:
        self.assertEqual(entry_for_keycap("sen"), ("sen(", "asin(", None))
        self.assertEqual(entry_for_keycap("log"), ("log(", "ln(", "logbase("))
        self.assertEqual(entry_for_keycap("Ans"), ("Ans", "HISTORY", None))
        self.assertEqual(entry_for_keycap("AC"), ("AC", "BLACKOUT", None))

    def test_keycaps_that_differ_from_the_screen_labels(self) -> None:
        self.assertEqual(entry_for_keycap("x^-1"), ("inv(", None, None))
        self.assertEqual(entry_for_keycap("Del"), ("DEL", None, None))
        # A tecla "," é a posição do "." da tela: decimal; Shift dá a vírgula.
        self.assertEqual(entry_for_keycap(","), (".", None, ","))

    def test_question_mark_has_a_spoken_answer(self) -> None:
        self.assertIsNone(entry_for_keycap("?"))
        self.assertTrue(NO_FUNCTION_SPEECH.strip())


class MatrixInputPumpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = FakeRoot()
        self.keyboard = FakeKeyboard()
        self.pressed: list[tuple] = []
        self.unmapped: list[KeyEvent] = []
        self.pump = MatrixInputPump(
            self.root, self.keyboard,
            on_press=lambda *entry: self.pressed.append(entry),
            on_unmapped=self.unmapped.append,
        )
        self.pump.start()

    def deliver(self, *events: KeyEvent) -> None:
        for item in events:
            self.keyboard.sink(item)  # como a thread de varredura faria
        self.pump.tick()

    def test_start_attaches_and_schedules(self) -> None:
        self.assertIsNotNone(self.keyboard.sink)
        self.assertEqual(self.root.scheduled[0][1], self.pump.tick)

    def test_digit_press_reaches_the_front(self) -> None:
        self.deliver(event("7"))
        self.assertEqual(self.pressed, [("7", None, None)])

    def test_press_carries_the_ctrl_and_shift_functions(self) -> None:
        self.deliver(event("sen"))
        self.assertEqual(self.pressed, [("sen(", "asin(", None)])

    def test_release_is_not_input(self) -> None:
        self.deliver(event("7", pressed=False))
        self.assertEqual(self.pressed, [])
        self.assertEqual(self.unmapped, [])

    def test_question_mark_goes_to_the_unmapped_handler(self) -> None:
        self.deliver(event("?"))
        self.assertEqual(self.pressed, [])
        self.assertEqual([e.keycap for e in self.unmapped], ["?"])

    def test_events_are_handled_in_arrival_order(self) -> None:
        self.deliver(event("Ctrl"), event("sen"))
        self.assertEqual(self.pressed, [("Ctrl", None, None), ("sen(", "asin(", None)])

    def test_tick_always_reschedules_even_if_the_front_fails(self) -> None:
        def broken(*_entry):
            raise RuntimeError("bug no front")

        self.pump.on_press = broken
        before = len(self.root.scheduled)
        with self.assertRaises(RuntimeError):
            self.deliver(event("7"))
        self.assertEqual(len(self.root.scheduled), before + 1)

    def test_stop_detaches_and_ends_the_polling(self) -> None:
        self.pump.stop()
        self.assertIsNone(self.keyboard.sink)
        before = len(self.root.scheduled)
        self.pump.tick()
        self.assertEqual(len(self.root.scheduled), before)


if __name__ == "__main__":
    unittest.main()
