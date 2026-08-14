"""Audio-only operation for when no usable video output exists (RF-04).

PRD §7.3: audio feedback runs in parallel with whatever video is available, and
when there is none the calculator must still be operable "apoiada no audio".
This loop reads the physical keyboard and announces every entry and result via
TTS, using the same core state machine and the same PRD §13 error catalogue as
the visual fronts - no Tk window is created.
"""

from __future__ import annotations

import logging

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
from software.hw_platform.keyboard import KeyboardAdapter
from software.ui_common.error_messages import friendly_message, spoken_priority_prefix
from software.ui_common.keypad import spoken_token

logger = logging.getLogger(__name__)

_QUIT_COMMANDS = {"sair", "quit", "exit"}
_HELP_TEXT = (
    "Modo somente audio. Digite uma expressao e pressione Enter para calcular. "
    "Escreva 'sair' para encerrar."
)


class AudioOnlyCalculator:
    """Keyboard-in / speech-out calculator with no visual surface."""

    def __init__(
        self,
        state: CalculatorState | None = None,
        speech: SpeechService | None = None,
        keyboard: KeyboardAdapter | None = None,
    ) -> None:
        self.state = state or CalculatorState()
        self.speech = speech or SpeechService()
        self.keyboard = keyboard or KeyboardAdapter()

    def run(self) -> None:
        self.speech.say("Calculadora pronta. Sem video disponivel, modo somente audio.")
        print(_HELP_TEXT)
        try:
            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line.lower() in _QUIT_COMMANDS:
                    break
                self.submit(line)
        except KeyboardInterrupt:
            pass
        finally:
            self.speech.say("Encerrando")
            self.speech.stop()

    def submit(self, line: str) -> None:
        """Feed one typed expression through the shared state machine."""
        self.state.press("AC")
        for char in line:
            token = self.keyboard.map_key(char) or char
            self.state.press(token)

        result = self.state.press("=")
        if result is None:
            return
        self.announce(result)

    def announce(self, result) -> None:
        if result.ok:
            message = f"Resultado {result.display}"
            print(message)
            self.speech.interrupt_and_say(message)
            return

        # Same code and priority prefix the visual fronts use (PRD §13).
        friendly_msg = friendly_message(result.code, result.message)
        prefix = spoken_priority_prefix(result.code)
        print(f"{result.code}: {friendly_msg}")
        self.speech.interrupt_and_say(
            f"{prefix} {result.code.split('-')[-1]}. {friendly_msg}"
        )

    def announce_token(self, token: str) -> None:
        """Announce a single key press (used when driven key-by-key)."""
        self.speech.say(spoken_token(token))


def main() -> None:
    AudioOnlyCalculator().run()


if __name__ == "__main__":
    main()
