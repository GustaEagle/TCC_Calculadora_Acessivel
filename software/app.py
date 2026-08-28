"""Entry point: picks the front-end that matches the active video output.

PRD §7 decides *where* the calculator is visible, so that choice belongs here
rather than in any UI package: the external monitor wins when recognised
(RF-02/RF-03), the LCD is used when it is the only panel available, and with no
usable video the calculator falls back to audio-only operation (RF-04).
Exactly one front is started per run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    SimulatedHdmiPortReader,
    SysfsHdmiPortReader,
)

# CLI names for --force-mode, kept short for demos and debugging sessions.
_FORCED_MODES = {
    "lcd": DisplayMode.LCD,
    "hdmi": DisplayMode.HDMI,
    "audio": DisplayMode.AUDIO_ONLY,
}


def resolve_mode(force_mode: str | None = None, selector: DisplaySelector | None = None) -> DisplayMode:
    """Active output, honouring --force-mode when given."""
    if force_mode is not None:
        return _FORCED_MODES[force_mode]
    return (selector or DisplaySelector()).current_mode()


def run_mode(mode: DisplayMode) -> int:
    """Start the single front-end matching `mode`, returning its exit code.

    UI modules are imported lazily so audio-only operation never needs a Tk
    runtime, and so a headless machine can still run the audio path.

    The visual fronts return VIDEO_CHANGED_EXIT when the active output changed
    under them (RF-09) — the kiosk loop restarts the session so the other front
    comes up on the panel that is now there.
    """
    if mode == DisplayMode.HDMI:
        from software.ui.hdmi.app import CalculatorApp

        return CalculatorApp().run() or 0

    if mode == DisplayMode.LCD:
        from software.ui.lcd.app import CalculatorApp

        return CalculatorApp().run() or 0

    from software.audio_only import AudioOnlyCalculator

    AudioOnlyCalculator().run()
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
    return parser


def print_outputs() -> None:
    """Diagnostic for the image bring-up (PRD §6/§11).

    The cabling is fixed - HDMI0 is the LCD, HDMI1 the monitor - but the DRM
    connector names the kernel gives those ports are not guaranteed, so print
    what this machine actually exposes and which name each role is bound to.
    """
    reader = SysfsHdmiPortReader()
    connectors = reader.list_connectors()

    if not connectors:
        print(f"Nenhum conector encontrado em {reader.drm_path} (maquina sem DRM?).")
    else:
        for name, status in connectors.items():
            print(f"{name}: {status}")

    print()
    print(f"LCD (HDMI0)     -> {reader.lcd_connector}")
    print(f"Monitor (HDMI1) -> {reader.monitor_connector}")
    print(f"Deteccao real disponivel: {'sim' if reader.available() else 'nao (usando simulacao)'}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_outputs:
        print_outputs()
        return 0

    selector = None
    if args.simulate_monitor:
        selector = DisplaySelector(SimulatedHdmiPortReader(monitor_present=True))

    return run_mode(resolve_mode(args.force_mode, selector))


if __name__ == "__main__":
    raise SystemExit(main())
