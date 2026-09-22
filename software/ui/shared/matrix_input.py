"""Bring keypad-matrix presses into the Tk event loop (RF-05).

The matrix is swept in its own thread (hw_platform/keypad_matrix.py): a sweep
blocks for ~8 ms, which the Tk loop cannot afford ~100 times a second. Tk is
not thread-safe, so the thread only enqueues; this pump drains the queue from
`root.after`, the same shape as VideoOutputWatch, and hands each press to the
front's own `_handle_token()`. The physical keys therefore go through exactly
the path the PC keyboard uses — Ctrl/Shift, history, blackout, speech — with
the Ctrl and Shift functions of each key taken from the shared catalogue.

Kept out of ui/lcd and ui/hdmi so both fronts share one behaviour and the
pump stays testable with a fake root.
"""

from __future__ import annotations

import logging
import queue
from typing import Callable

from software.hw_platform.keypad_matrix import KeyEvent, MatrixKeyboard
from software.ui.shared.keypad import entry_for_keycap

logger = logging.getLogger(__name__)

POLL_INTERVAL_MS = 10

PressHandler = Callable[[str, "str | None", "str | None"], None]


class MatrixInputPump:
    """Drain matrix events on the Tk thread and feed them to the front."""

    def __init__(
        self,
        root,
        keyboard: MatrixKeyboard,
        on_press: PressHandler,
        on_unmapped: Callable[[KeyEvent], None],
        interval_ms: int = POLL_INTERVAL_MS,
    ) -> None:
        self.root = root
        self.keyboard = keyboard
        self.on_press = on_press
        self.on_unmapped = on_unmapped
        self.interval_ms = interval_ms
        self.events: queue.Queue[KeyEvent] = queue.Queue()
        self._stopped = False

    def start(self) -> None:
        self.keyboard.attach(self.events.put_nowait)
        self.root.after(self.interval_ms, self.tick)

    def stop(self) -> None:
        self._stopped = True
        self.keyboard.detach()

    def tick(self) -> None:
        if self._stopped:
            return
        try:
            while True:
                try:
                    event = self.events.get_nowait()
                except queue.Empty:
                    break
                self.dispatch(event)
        finally:
            # Reagendado mesmo se o front falhar numa tecla: senão a matriz
            # morreria em silêncio. Também devolve o controlo ao Python dentro
            # do mainloop do Tk, para o handler de SIGTERM correr logo (app.py).
            self.root.after(self.interval_ms, self.tick)

    def dispatch(self, event: KeyEvent) -> None:
        logger.debug("matriz: %s %s %s %r", event.state, event.switch, event.coord, event.keycap)
        if not event.pressed:
            return
        entry = entry_for_keycap(event.keycap)
        if entry is None:
            self.on_unmapped(event)
            return
        self.on_press(*entry)
