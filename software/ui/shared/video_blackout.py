"""Switch every screen off and back on, by the user's command (video-blackout).

The calculator does not depend on the screen (RF-04): a blind user gains
nothing from a lit panel and pays for it in UPS battery and in privacy. The
command turns every output off while the front keeps running - keys still
arrive, results are still spoken - which is what separates it from
DisplayMode.AUDIO_ONLY, the state for *no video hardware at all*.

The blackout is session state (design D1), not a DisplayMode and not part of
CalculatorState: the entry point builds one VideoBlackout per run and hands it
to every front, so a front rebuilt by RF-09 is born dark too, exactly the way
the same CalculatorState keeps the expression across the swap. It is never
persisted: every boot starts lit.

Kept out of ui/lcd and ui/hdmi (like video_watch.py) so both fronts share one
behaviour, and free of Tk so it is testable with a fake applier.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from software.hw_platform.display import DisplayMode

logger = logging.getLogger(__name__)

# Ctrl + AC (design D4): the matrix has no free key, so the command is AC's
# secondary function - the same model as Ctrl + Ans for the history.
BLACKOUT_TOKEN = "BLACKOUT"

# The key the blackout sentence names as the way back: AC alone relights (D5),
# and it is the same key on the PC (Esc).
RELIGHT_KEY_NAME = "AC"

# Applies `VideoBlackout.active` to the X server: the panel it pointed X at
# (any mode when switching off), or None when the change was not confirmed.
VideoApplier = Callable[[], DisplayMode | None]


@dataclass
class VideoBlackout:
    """Whether the user switched the screens off in this session."""

    active: bool = False


# PRD §13, WRN-013 (P2). With the screens off the voice is the only proof the
# command worked, and the only way to learn how to undo it.
_PANEL_NAMES = {
    DisplayMode.HDMI: "no monitor externo",
    DisplayMode.LCD: "na tela da calculadora",
}


def blackout_speech() -> str:
    return f"Aviso 013. Telas desligadas. Para religar, pressione {RELIGHT_KEY_NAME}."


def relit_speech(mode: DisplayMode) -> str:
    return f"Aviso 013. Tela religada {_PANEL_NAMES.get(mode, 'na saída disponível')}."


def blackout_failed_speech() -> str:
    return "Aviso 013. Não foi possível desligar as telas."


def relight_failed_speech() -> str:
    return "Aviso 013. Não foi possível religar a tela."


def no_video_control() -> DisplayMode | None:
    """Applier for a front started on its own, outside the entry point.

    Only software/app.py knows how to point X at a panel; a front built
    directly (development, tests) reports the command as not confirmed, which
    is the honest answer - nothing was switched.
    """
    logger.warning("WRN-013 front sem controle de video (iniciado fora do app)")
    return None


def toggle(session: VideoBlackout, apply: VideoApplier) -> str:
    """Ctrl + AC: flip the screens and return the sentence to speak.

    The flag is flipped *before* applying because the applier reads it (one
    point applies video, design D2), and flipped back when the change is not
    confirmed - announcing a blackout that did not happen would be a lie the
    user cannot see through.
    """
    switching_off = not session.active
    session.active = switching_off

    lit = apply()
    if lit is None:
        session.active = not switching_off
        logger.warning("WRN-013 comando de video nao confirmado (desligar=%s)", switching_off)
        return blackout_failed_speech() if switching_off else relight_failed_speech()

    logger.info("WRN-013 telas %s", "desligadas" if switching_off else f"religadas em {lit.value}")
    return blackout_speech() if switching_off else relit_speech(lit)


def relight_on_ac(session: VideoBlackout, apply: VideoApplier) -> str | None:
    """AC relights a dark screen: the way out for whoever pressed it by mistake.

    Returns the sentence to speak, or None when the screen was already lit - AC
    then keeps exactly its old meaning and the applier is not even called.
    """
    if not session.active:
        return None
    return toggle(session, apply)
