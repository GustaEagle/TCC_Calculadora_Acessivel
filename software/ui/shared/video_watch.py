"""Close the running front when the active video output changes (RF-09).

The external monitor is always plugged in with the calculator already on, so
the front that is up at that moment has to give way to the other one. Rather
than rebuilding the UI in place, the front simply exits with
VIDEO_CHANGED_EXIT: the kiosk session restarts it (and restarts X, which is
what actually lets a newly attached panel be used at its own resolution).
See system/rpi-os/alpine/overlay/home/kiosk/.xinitrc.

Kept out of ui/lcd and ui/hdmi so both fronts share one behaviour, and so the
polling logic stays testable with a fake widget instead of a real window.
"""

from __future__ import annotations

import logging

from software.hw_platform.display import DisplayMode, DisplayWatcher

logger = logging.getLogger(__name__)

# Exit code the kiosk loop reads as "video changed, restart the session".
# Distinct from 0 (user quit) and 1 (crash), which must not restart X.
VIDEO_CHANGED_EXIT = 75

POLL_INTERVAL_MS = 2000
# The announcement must finish before the window goes away: closing the app
# calls SpeechService.stop(), which terminates whatever is being spoken.
ANNOUNCE_GRACE_MS = 3000

# PRD §13, WRN-012 (P2): announced because the user may not be looking at any
# screen — losing or gaining the monitor is otherwise invisible to them.
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
        grace_ms: int = ANNOUNCE_GRACE_MS,
    ) -> None:
        self.root = root
        self.speech = speech
        self.watcher = watcher or DisplayWatcher(mode=mode)
        self.interval_ms = interval_ms
        self.grace_ms = grace_ms
        self.changed_to: DisplayMode | None = None

    def start(self) -> None:
        self.root.after(self.interval_ms, self.tick)

    def tick(self) -> None:
        new_mode = self.watcher.poll()
        if new_mode is None:
            self.root.after(self.interval_ms, self.tick)
            return

        logger.info("saida de video mudou para %s; encerrando o front", new_mode)
        self.changed_to = new_mode
        self.speech.interrupt_and_say(video_changed_speech(new_mode))
        # Let the warning be spoken before the window (and the process) go.
        self.root.after(self.grace_ms, self.root.destroy)

    @property
    def exit_code(self) -> int:
        """VIDEO_CHANGED_EXIT once a change closed the front, 0 otherwise."""
        return VIDEO_CHANGED_EXIT if self.changed_to is not None else 0
