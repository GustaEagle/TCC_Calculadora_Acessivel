#!/usr/bin/env python3
"""Interactive bring-up scanner for the physical 6x7 keypad matrix.

Usa o MESMO scanner do app (software/hw_platform/keypad_matrix.py), com a
polaridade validada no hardware: coluna ativa em saída HIGH, linhas em entrada
com pull-down, colunas inativas sem pull. Não precisa de vídeo, de X11 nem do
resto da aplicação — serve para responder, na bancada:

1. **As teclas fecham contacto?** Cada pressionamento e cada soltura aparecem
   na consola com keycap, coordenada `C#L#`, switch `SW#` e GPIOs.
2. **O mapa está certo?** O `Ctrl+C` imprime a grade 7x6 com os switches já
   vistos (38 esperados) — é a conferência tecla a tecla do mapa de
   software/hw_platform/keypad_pinout.py.

Uso típico (por SSH, com o Pi sem monitor, e com o app parado — ele segura as
mesmas GPIOs):

    python3 software/tools/keypad_bringup.py

e depois premir as teclas uma a uma. Ctrl-C imprime o relatório e devolve as
13 GPIOs a entrada sem bias.

Para caçar um fio do flat com multímetro/LED, `--toggle C3` (ou `L0`...) põe
esse condutor a piscar entre 0 V e 3,3 V, com os outros 12 em entrada sem
bias. `--list` imprime a pinagem e o mapa sem tocar no hardware.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.hw_platform.keypad_matrix import (  # noqa: E402
    CONSUMER,
    DEBOUNCE_S,
    SETTLE_S,
    SWEEP_PAUSE_S,
    Debouncer,
    GpiodMatrixIO,
    KeyEvent,
    MatrixOpenError,
    MatrixUnavailable,
    scan_once,
)
from software.hw_platform.keypad_pinout import (  # noqa: E402
    COL_BCM_PINS,
    COL_LINES,
    EMPTY_COORDS,
    GPIOCHIP_PATH,
    ROW_BCM_PINS,
    ROW_LINES,
    SHARED_FUNCTION_PINS,
    SWITCHES,
    MatrixLine,
    all_lines,
    switch_at,
)

LINES_BY_NAME: dict[str, MatrixLine] = {line.name: line for line in all_lines()}
_HEADER_PIN = {line.bcm: line.header_pin for line in all_lines()}

_INSTALL_HINT = (
    "\n\nRaspberry Pi OS:  sudo apt install python3-libgpiod"
    "\nAlpine (imagem):  apk add py3-libgpiod"
    "\n\nSe dá 'Permission denied', o utilizador não está no grupo dono de"
    "\n/dev/gpiochip0 (ver 99-gpio.rules). Se as linhas estão ocupadas, pare o"
    "\napp da calculadora: ele segura as mesmas GPIOs."
)


def describe_line(line: MatrixLine) -> str:
    return (
        f"{line.name} ({line.net}, GPIO{line.bcm}/pino {line.header_pin}, "
        f"fio {line.wire_color})"
    )


def describe_event(event: KeyEvent) -> str:
    return (
        f"  {event.state:<11} {event.switch:<5} {event.coord}  {event.keycap!r:<8} "
        f"coluna GPIO{event.col_bcm} (pino {_HEADER_PIN[event.col_bcm]})  "
        f"linha GPIO{event.row_bcm} (pino {_HEADER_PIN[event.row_bcm]})"
    )


def grid(seen: set[str]) -> str:
    """Grade 7x6: o switch se já foi visto, '.' se não, '—' onde não há switch."""
    out = ["      " + "".join(f"{line.name:>6}" for line in COL_LINES)]
    for row, row_line in enumerate(ROW_LINES):
        cells = []
        for col in range(len(COL_LINES)):
            sw = switch_at(col, row)
            if sw is None:
                cells.append("—")
            else:
                cells.append(sw.switch if sw.switch in seen else ".")
        out.append(f"  {row_line.name}  " + "".join(f"{c:>6}" for c in cells))
    out.append(f"\n  {len(seen)} de {len(SWITCHES)} switches vistos.")
    missing = [f"{sw.switch} {sw.coord} {sw.keycap!r}" for sw in SWITCHES if sw.switch not in seen]
    if missing and len(missing) <= 10:
        out.append("  Faltam: " + ", ".join(missing))
    return "\n".join(out)


def print_listing() -> None:
    print("Condutores (offset no gpiochip0 = BCM):")
    for line in all_lines():
        conflict = SHARED_FUNCTION_PINS.get(line.bcm)
        suffix = f"  [{conflict}]" if conflict else ""
        print(f"  {describe_line(line)}{suffix}")
    print("\nSwitches:")
    for sw in SWITCHES:
        col, row = COL_LINES[sw.col], ROW_LINES[sw.row]
        print(f"  {sw.switch:<5} {sw.coord}  {sw.keycap!r:<8} GPIO{col.bcm} -> GPIO{row.bcm}")
    empty = ", ".join(f"C{c}L{r}" for c, r in sorted(EMPTY_COORDS))
    print(f"\nPosições sem switch: {empty}")


def run_scan(
    io,
    settle_s: float,
    debounce_s: float,
    clock=time.monotonic,
    sleep=time.sleep,
    out=print,
) -> set[str]:
    """Varre até Ctrl-C, imprimindo cada evento; devolve os switches vistos."""
    out("Pinos da matriz com função alternativa (têm de estar desligados no boot):")
    for line in all_lines():
        if line.bcm in SHARED_FUNCTION_PINS:
            out(f"  {line.name}: GPIO{line.bcm} = {SHARED_FUNCTION_PINS[line.bcm]}")
    out("\nA varrer. Prima as teclas UMA A UMA. Ctrl-C termina e imprime o mapa.\n")

    debouncer = Debouncer(debounce_s)
    seen: set[str] = set()
    try:
        while True:
            closed = scan_once(io, settle_s, sleep)
            for event in debouncer.update(clock(), closed):
                out(describe_event(event))
                if event.pressed:
                    seen.add(event.switch)
            sleep(SWEEP_PAUSE_S)
    except KeyboardInterrupt:
        out("\n" + "=" * 72)
        out("MAPA linha x coluna")
        out(grid(seen))
        out("=" * 72)
    return seen


def run_toggle(line: MatrixLine, chip_path: str = GPIOCHIP_PATH, cycles: int | None = None,
               half_period_s: float = 0.5, sleep=time.sleep) -> None:
    """Pisca UM condutor entre 0 V e 3,3 V; os outros 12 ficam sem bias.

    Uma única saída de cada vez, portanto nunca há duas saídas com níveis
    opostos. As 13 linhas são requisitadas juntas (e não só a do alvo) para o
    estado das outras ser explícito e para falhar se o app as estiver a usar.
    """
    import gpiod
    from gpiod.line import Bias, Direction, Value

    floating = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.DISABLED)
    output = gpiod.LineSettings(
        direction=Direction.OUTPUT, bias=Bias.DISABLED, output_value=Value.INACTIVE
    )
    config = {bcm: floating for bcm in ROW_BCM_PINS + COL_BCM_PINS}
    config[line.bcm] = output
    request = gpiod.request_lines(chip_path, consumer=f"{CONSUMER}-toggle", config=config)
    try:
        high = False
        done = 0
        while cycles is None or done < cycles:
            high = not high
            request.set_value(line.bcm, Value.ACTIVE if high else Value.INACTIVE)
            sleep(half_period_s)
            if not high:
                done += 1
    except KeyboardInterrupt:
        print()
    finally:
        try:
            request.reconfigure_lines({bcm: floating for bcm in ROW_BCM_PINS + COL_BCM_PINS})
        finally:
            request.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--chip", default=GPIOCHIP_PATH,
        help=f"caminho do gpiochip (padrão {GPIOCHIP_PATH}; só o Pi 4 é suportado)",
    )
    parser.add_argument(
        "--settle-ms", type=float, default=SETTLE_S * 1000,
        help=f"espera após ativar cada coluna, em ms (padrão {SETTLE_S * 1000:g})",
    )
    parser.add_argument(
        "--debounce-ms", type=float, default=DEBOUNCE_S * 1000,
        help=f"tempo de estabilidade para validar uma mudança, em ms (padrão {DEBOUNCE_S * 1000:g})",
    )
    parser.add_argument(
        "--toggle", metavar="Cx|Lx",
        help="em vez de varrer, pisca um condutor (C0..C6, L0..L5) para o localizar no flat",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="imprime a pinagem e o mapa de switches e sai (não toca no hardware)",
    )
    args = parser.parse_args(argv)

    if args.list:
        print_listing()
        return 0

    if args.toggle:
        line = LINES_BY_NAME.get(args.toggle.upper())
        if line is None:
            raise SystemExit(f"condutor desconhecido: {args.toggle} (use C0..C6 ou L0..L5)")
        print(f"A piscar {describe_line(line)}")
        print("1 Hz entre 0 V e 3,3 V. Meça com o multímetro na ponta do flat. Ctrl-C para.")
        try:
            run_toggle(line, args.chip)
        except (ImportError, OSError) as exc:
            raise SystemExit(f"não foi possível usar {args.chip}: {exc}{_INSTALL_HINT}") from exc
        return 0

    try:
        io = GpiodMatrixIO(args.chip, consumer=f"{CONSUMER}-bringup")
    except (MatrixUnavailable, MatrixOpenError) as exc:
        raise SystemExit(f"Matriz indisponível: {exc}{_INSTALL_HINT}") from exc
    print(f"libgpiod v2 em {args.chip}\n")
    try:
        run_scan(io, args.settle_ms / 1000, args.debounce_ms / 1000)
    finally:
        # Sempre: as 13 GPIOs voltam a entrada sem bias antes de libertar.
        io.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
