"""Entry point: picks the front-end that matches the active video output.

PRD §7 decides *where* the calculator is visible, so that choice belongs here
rather than in any UI package: the external monitor wins when recognised
(RF-02/RF-03), the LCD is used when it is the only panel available, and with no
usable video the calculator falls back to audio-only operation (RF-04).
Exactly one front is started per run.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
from software.hw_platform import video_output
from software.hw_platform.display import (
    DEFAULT_LCD_CONNECTOR,
    DEFAULT_MONITOR_CONNECTOR,
    LCD_CONNECTOR_ENV,
    MONITOR_CONNECTOR_ENV,
    DisplayMode,
    DisplaySelector,
    SimulatedHdmiPortReader,
    SysfsHdmiPortReader,
)

logger = logging.getLogger(__name__)

# CLI names for --force-mode, kept short for demos and debugging sessions.
_FORCED_MODES = {
    "lcd": DisplayMode.LCD,
    "hdmi": DisplayMode.HDMI,
    "audio": DisplayMode.AUDIO_ONLY,
}

LOG_FILE_ENV = "CALC_LOG_FILE"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def default_log_path() -> Path:
    """`$HOME/calculadora.log` - the kiosk user's home, created by the build.

    Not /var/log: the rootfs is writable but `kiosk` is an ordinary user with
    no guaranteed write permission there, and a boot must not depend on it.
    """
    return Path(os.path.expanduser("~")) / "calculadora.log"


def configure_logging() -> None:
    """Send the log somewhere readable on the image (D4).

    On the kiosk, tty1 is covered by X, so a warning on stderr is invisible and
    a failed xrandr is indistinguishable from a working one. Only the entry
    point configures handlers; modules just call getLogger(__name__).
    """
    path = os.environ.get(LOG_FILE_ENV) or str(default_log_path())

    handler: logging.Handler
    try:
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError as exc:  # unwritable path must not stop the calculator
        handler = logging.StreamHandler()
        logging.basicConfig(level=logging.INFO, handlers=[handler], format=_LOG_FORMAT, force=True)
        logger.warning("nao foi possivel abrir %s (%s); registrando em stderr", path, exc)
        return

    logging.basicConfig(level=logging.INFO, handlers=[handler], format=_LOG_FORMAT, force=True)


def resolve_mode(force_mode: str | None = None, selector: DisplaySelector | None = None) -> DisplayMode:
    """Active output, honouring --force-mode when given."""
    if force_mode is not None:
        return _FORCED_MODES[force_mode]
    return (selector or DisplaySelector()).current_mode()


def resolve_output_names() -> tuple[str, str]:
    """The xrandr names for the LCD and the monitor, in that order.

    The X outputs are read once and reused for both roles, so resolving the
    pair costs a single `xrandr --query` instead of one per panel.
    """
    outputs = video_output.read_outputs()
    lcd = video_output.output_name(
        os.environ.get(LCD_CONNECTOR_ENV, DEFAULT_LCD_CONNECTOR),
        video_output.LCD_OUTPUT_ENV,
        outputs,
    )
    monitor = video_output.output_name(
        os.environ.get(MONITOR_CONNECTOR_ENV, DEFAULT_MONITOR_CONNECTOR),
        video_output.MONITOR_OUTPUT_ENV,
        outputs,
    )
    return lcd, monitor


def point_x_at(mode: DisplayMode) -> None:
    """Enable the panel `mode` belongs to and switch the other one off.

    X keeps driving whatever it configured at startup, so a monitor plugged in
    later stays dark until xrandr enables it, and with both ports connected it
    autoconfigures an extended desktop that PRD §7.2 forbids. Best effort: off
    the Pi there is no X server and this is a no-op.
    """
    if mode == DisplayMode.AUDIO_ONLY:
        return

    lcd, monitor = resolve_output_names()
    target = monitor if mode == DisplayMode.HDMI else lcd
    video_output.activate(target, disable=(lcd, monitor), mode=mode.value)


def start_front(
    mode: DisplayMode, state: CalculatorState, speech: SpeechService
) -> DisplayMode | None:
    """Run the single front matching `mode`; returns the mode taking over.

    UI modules are imported lazily so audio-only operation never needs a Tk
    runtime, and so a headless machine can still run the audio path.
    """
    if mode == DisplayMode.HDMI:
        from software.ui.hdmi.app import CalculatorApp

        return CalculatorApp(state, speech).run()

    if mode == DisplayMode.LCD:
        from software.ui.lcd.app import CalculatorApp

        return CalculatorApp(state, speech).run()

    from software.audio_only import AudioOnlyCalculator

    AudioOnlyCalculator(state, speech).run()
    return None


def run_mode(
    mode: DisplayMode,
    state: CalculatorState | None = None,
    speech: SpeechService | None = None,
) -> int:
    """Run fronts until the user quits, swapping when the video output changes.

    RF-09: the monitor is always plugged in with the calculator already on, so
    the swap has to be cheap. The whole point of the loop is that `state` is
    built once and handed to whichever front comes next — the expression being
    typed, the history and the angle mode survive; nothing restarts.
    """
    state = state or CalculatorState()
    speech = speech or SpeechService()

    next_mode: DisplayMode | None = mode
    while next_mode is not None:
        point_x_at(next_mode)
        next_mode = start_front(next_mode, state, speech)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calculadora",
        description="Calculadora cientifica acessivel (TCC).",
    )
    parser.add_argument(
        "--force-mode",
        choices=sorted(_FORCED_MODES),
        help=(
            "Forca a saida em vez de detectar (desenvolvimento/demonstracao): "
            "lcd = painel 4.3\", hdmi = monitor externo, audio = somente voz."
        ),
    )
    parser.add_argument(
        "--simulate-monitor",
        action="store_true",
        help="Simula um monitor externo reconhecido (sem hardware real).",
    )
    parser.add_argument(
        "--list-outputs",
        action="store_true",
        help=(
            "Lista os conectores de video vistos pelo sistema e encerra "
            "(usado no bring-up para confirmar quais nomes correspondem a "
            "HDMI0/HDMI1)."
        ),
    )
    parser.add_argument(
        "--apply-video-layout",
        action="store_true",
        help=(
            "Aplica o layout exclusivo de video (uma unica saida ativa) e "
            "encerra, sem abrir nenhuma interface. Chamado pela sessao grafica "
            "antes de subir o app, para que o desktop estendido que o X "
            "autoconfigura nunca chegue a ficar visivel (PRD §7.2)."
        ),
    )
    return parser


def print_outputs() -> None:
    """Diagnostic for the image bring-up (PRD §6/§11).

    The cabling is fixed - HDMI0 is the LCD, HDMI1 the monitor - but neither
    the DRM connector names nor the xrandr output names are guaranteed, and a
    mismatch between the two is what left both panels lit. Print both sides and
    the mapping actually in use, so one command answers the whole checklist.
    """
    reader = SysfsHdmiPortReader()
    connectors = reader.list_connectors()

    print("Conectores DRM (kernel):")
    if not connectors:
        print(f"  nenhum encontrado em {reader.drm_path} (maquina sem DRM?)")
    else:
        for name, status in connectors.items():
            print(f"  {name}: {status}")

    print()
    print("Saidas do servidor X (xrandr):")
    if video_output.missing_xrandr_on_x():
        # A saída exclusiva do §7.2 é aplicada por xrandr; sem o binário, tudo
        # aqui vira no-op e as duas telas ficam acesas.
        print("  ERRO: o X esta a correr mas o 'xrandr' NAO esta instalado.")
        print("  Sem ele nenhuma reconfiguracao de saida acontece (PRD §7.2).")
        print("  Corrija com: apk add xrandr   (e ver system/rpi-os/alpine/packages)")
    else:
        outputs = video_output.read_outputs()
        if not outputs:
            print("  nenhuma (sem DISPLAY, sem xrandr, ou estado ilegivel)")
        else:
            for name, active in outputs.items():
                print(f"  {name}: {'ativa' if active else 'inativa'}")

    lcd_output, monitor_output = resolve_output_names()
    print()
    print("Mapeamento em uso (conector DRM -> saida X):")
    print(f"  LCD (HDMI0)     -> {reader.lcd_connector} -> {lcd_output}")
    print(f"  Monitor (HDMI1) -> {reader.monitor_connector} -> {monitor_output}")
    print(f"Deteccao real disponivel: {'sim' if reader.available() else 'nao (usando simulacao)'}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()

    # Diagnostics first: --list-outputs only reports, so it stays useful even
    # when combined with the flags that would otherwise change the screen.
    if args.list_outputs:
        print_outputs()
        return 0

    selector = None
    if args.simulate_monitor:
        selector = DisplaySelector(SimulatedHdmiPortReader(monitor_present=True))

    mode = resolve_mode(args.force_mode, selector)

    if args.apply_video_layout:
        # No front, no Tk import: the graphical session runs this before the
        # app so the autoconfigured extended desktop is never drawn on.
        point_x_at(mode)
        return 0

    return run_mode(mode)


if __name__ == "__main__":
    raise SystemExit(main())
