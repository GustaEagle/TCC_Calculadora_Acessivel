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


def run_mode(mode: DisplayMode) -> None:
    """Start the single front-end matching `mode`.

    UI modules are imported lazily so audio-only operation never needs a Tk
    runtime, and so a headless machine can still run the audio path.
    """
    if mode == DisplayMode.HDMI:
        from software.ui.hdmi.app import CalculatorApp

        CalculatorApp().run()
        return

    if mode == DisplayMode.LCD:
        from software.ui.lcd.app import CalculatorApp

        CalculatorApp().run()
        return

    from software.audio_only import AudioOnlyCalculator

    AudioOnlyCalculator().run()


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
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    selector = None
    if args.simulate_monitor:
        selector = DisplaySelector(SimulatedHdmiPortReader(monitor_present=True))

    run_mode(resolve_mode(args.force_mode, selector))


if __name__ == "__main__":
    main()
