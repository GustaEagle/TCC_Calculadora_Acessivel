"""Hand the UI over to the other front when the video output changes (RF-09).

The external monitor is always plugged in with the calculator already running,
so this is the normal flow and it has to be cheap: the front closes its window
and returns the mode that should take over, in the SAME process. The entry
point then builds the other front around the SAME CalculatorState, so the
expression being typed, the history and the angle mode all survive the swap —
nothing restarts, nothing is lost.

Kept out of ui/lcd and ui/hdmi so both fronts share one behaviour, and so the
polling logic stays testable with a fake widget instead of a real window.
"""

from __future__ import annotations

import logging

from software.hw_platform.display import DisplayMode, DisplayWatcher

logger = logging.getLogger(__name__)

POLL_INTERVAL_MS = 2000

# PRD §13, WRN-012 (P2): announced because the user may not be looking at any
# screen — losing or gaining the monitor is otherwise invisible to them. The
# speech keeps playing across the swap: the SpeechService is not torn down.
_SPOKEN_TARGET = {
    DisplayMode.HDMI: "Passando para o monitor externo.",
    DisplayMode.LCD: "Passando para a tela da calculadora.",
    DisplayMode.AUDIO_ONLY: "Sem video disponivel. Passando para o modo somente audio.",
}


def video_changed_speech(mode: DisplayMode) -> str:
    return f"Aviso 012. Saida de video alterada. {_SPOKEN_TARGET[mode]}"


class VideoOutputWatch:
    """Poll the video output from the Tk event loop and close on a change."""

    def __init__(
        self,
        root,
        speech,
        mode: DisplayMode,
        watcher: DisplayWatcher | None = None,
        interval_ms: int = POLL_INTERVAL_MS,
    ) -> None:
        self.root = root
        self.speech = speech
        self.watcher = watcher or DisplayWatcher(mode=mode)
        self.interval_ms = interval_ms
        self.changed_to: DisplayMode | None = None

    def start(self) -> None:
        self.root.after(self.interval_ms, self.tick)

    def tick(self) -> None:
        new_mode = self.watcher.poll()
        if new_mode is None:
            self.root.after(self.interval_ms, self.tick)
            return

        logger.info("saida de video mudou para %s; cedendo o front", new_mode)
        self.changed_to = new_mode
        self.speech.interrupt_and_say(video_changed_speech(new_mode))
        # No grace delay needed: the process (and the TTS worker) live on, so
        # the warning keeps playing while the other front is built.
        self.root.destroy()
