#!/usr/bin/env python3
"""Interactive bring-up scanner for the physical 6x7 keypad matrix.

Esta ferramenta responde às três perguntas que `docs/raspberry-pi-4b/pinout.md`
§6.5 deixa em aberto, sem precisar de vídeo, de X11 nem do resto da aplicação:

1. **As teclas fecham contacto?** Cada tecla premida aparece impressa na consola.
2. **Qual o sentido da varredura?** Não assume nada sobre a orientação dos
   díodos 1N4148: varre os 13 condutores nos DOIS sentidos (cada linha é posta
   a 0 V à vez, as outras 12 ficam em entrada com pull-up) e regista qual dos
   dois lados do par é que tem de ser o "driver". Só um sentido conduz — é esse
   o sentido que o scanner definitivo terá de usar.
3. **Que tecla está em que (linha, coluna)?** A tabela final imprime a grelha
   6x7 com as posições já vistas, que é o mapa que falta para ligar a matriz
   aos tokens de software/ui/shared/keypad.py.

Uso típico (por SSH, com o Pi sem monitor):

    python3 software/tools/keypad_bringup.py

e depois premir as teclas uma a uma. Ctrl-C imprime o relatório.

Para caçar um fio do flat com multímetro/LED, `--toggle L1` põe essa linha a
piscar entre 0 V e 3,3 V.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.hw_platform.keypad_pinout import (  # noqa: E402
    COL_LINES,
    ROW_LINES,
    SHARED_FUNCTION_PINS,
    MatrixLine,
    all_lines,
)

ROW_NAMES: tuple[str, ...] = tuple(line.name for line in ROW_LINES)
COL_NAMES: tuple[str, ...] = tuple(line.name for line in COL_LINES)
LINES_BY_NAME: dict[str, MatrixLine] = {line.name: line for line in all_lines()}

# Tempo entre pôr a linha a 0 V e ler as outras. O pull-up interno do Pi é
# fraco (~50 kΩ) e o flat tem capacitância: com menos que isto a subida de volta
# a 3,3 V pode não ter acabado e aparecem contactos fantasma.
DEFAULT_SETTLE_US = 300

# Quantas varreduras seguidas um par tem de aparecer para contar como tecla
# premida. É o debounce — o switch Cherry MX ressalta uns milissegundos.
DEFAULT_STABLE = 3


class GpioBackend:
    """input-pullup / output-low / read sobre um chip GPIO."""

    name = "?"

    def input_pullup(self, bcm: int) -> None:
        raise NotImplementedError

    def output_low(self, bcm: int) -> None:
        raise NotImplementedError

    def output_high(self, bcm: int) -> None:
        raise NotImplementedError

    def read(self, bcm: int) -> int:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class LgpioBackend(GpioBackend):
    """libgpiod/lgpio — o caminho suportado no Raspberry Pi OS Bookworm."""

    name = "lgpio"

    def __init__(self, chip: int) -> None:
        import lgpio

        self._lg = lgpio
        self._handle = lgpio.gpiochip_open(chip)
        self._claimed: set[int] = set()

    def _free(self, bcm: int) -> None:
        if bcm in self._claimed:
            self._lg.gpio_free(self._handle, bcm)
            self._claimed.discard(bcm)

    def input_pullup(self, bcm: int) -> None:
        self._free(bcm)
        self._lg.gpio_claim_input(self._handle, bcm, self._lg.SET_PULL_UP)
        self._claimed.add(bcm)

    def output_low(self, bcm: int) -> None:
        self._free(bcm)
        self._lg.gpio_claim_output(self._handle, bcm, 0)
        self._claimed.add(bcm)

    def output_high(self, bcm: int) -> None:
        self._free(bcm)
        self._lg.gpio_claim_output(self._handle, bcm, 1)
        self._claimed.add(bcm)

    def read(self, bcm: int) -> int:
        return self._lg.gpio_read(self._handle, bcm)

    def close(self) -> None:
        for bcm in list(self._claimed):
            self._free(bcm)
        self._lg.gpiochip_close(self._handle)


class GpiodBackend(GpioBackend):
    """py3-libgpiod v2 — é o que existe no Alpine (a imagem do produto).

    A API v2 não tem "claim solto por pino": pede-se as 13 linhas de uma vez e
    muda-se a configuração do conjunto. Por isso o backend guarda o modo de
    cada pino e reconfigura tudo a cada troca — uma ioctl por troca, na mesma
    ordem de grandeza do lgpio.
    """

    name = "gpiod (libgpiod v2)"

    def __init__(self, chip: int) -> None:
        import gpiod
        from gpiod.line import Bias, Direction, Value

        self._gpiod = gpiod
        self._bias, self._direction, self._value = Bias, Direction, Value
        self._modes = {line.bcm: "in" for line in all_lines()}
        self._request = gpiod.request_lines(
            f"/dev/gpiochip{chip}",
            consumer="keypad-bringup",
            config={bcm: self._settings("in") for bcm in self._modes},
        )

    def _settings(self, mode: str):
        if mode == "in":
            return self._gpiod.LineSettings(
                direction=self._direction.INPUT, bias=self._bias.PULL_UP
            )
        return self._gpiod.LineSettings(
            direction=self._direction.OUTPUT,
            output_value=(
                self._value.ACTIVE if mode == "high" else self._value.INACTIVE
            ),
        )

    def _apply(self, bcm: int, mode: str) -> None:
        self._modes[bcm] = mode
        self._request.reconfigure_lines(
            {pin: self._settings(m) for pin, m in self._modes.items()}
        )

    def input_pullup(self, bcm: int) -> None:
        self._apply(bcm, "in")

    def output_low(self, bcm: int) -> None:
        self._apply(bcm, "low")

    def output_high(self, bcm: int) -> None:
        self._apply(bcm, "high")

    def read(self, bcm: int) -> int:
        return 1 if self._request.get_value(bcm) == self._value.ACTIVE else 0

    def close(self) -> None:
        self._request.release()


class RpiGpioBackend(GpioBackend):
    """RPi.GPIO — reserva, caso o lgpio não esteja instalado."""

    name = "RPi.GPIO"

    def __init__(self) -> None:
        import RPi.GPIO as GPIO

        self._gpio = GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

    def input_pullup(self, bcm: int) -> None:
        self._gpio.setup(bcm, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)

    def output_low(self, bcm: int) -> None:
        self._gpio.setup(bcm, self._gpio.OUT, initial=self._gpio.LOW)

    def output_high(self, bcm: int) -> None:
        self._gpio.setup(bcm, self._gpio.OUT, initial=self._gpio.HIGH)

    def read(self, bcm: int) -> int:
        return int(self._gpio.input(bcm))

    def close(self) -> None:
        self._gpio.cleanup()


def open_backend(chip: int) -> GpioBackend:
    """Primeira biblioteca de GPIO que abrir o chip, na ordem de preferência.

    lgpio primeiro porque é o caminho do Raspberry Pi OS, onde o bring-up
    acontece; gpiod a seguir porque é o que a imagem Alpine do produto tem
    (py3-libgpiod); RPi.GPIO por último, como rede de segurança em sistemas
    antigos.
    """
    errors: list[str] = []
    for label, factory in (
        ("lgpio", lambda: LgpioBackend(chip)),
        ("gpiod", lambda: GpiodBackend(chip)),
        ("RPi.GPIO", RpiGpioBackend),
    ):
        try:
            return factory()
        except Exception as exc:  # ImportError, permissão, chip errado...
            errors.append(f"{label}: {exc}")
    raise SystemExit(
        "Nenhuma biblioteca de GPIO utilizável.\n  "
        + "\n  ".join(errors)
        + "\n\nRaspberry Pi OS:  sudo apt install python3-lgpio"
        + "\nAlpine (imagem):  apk add py3-libgpiod"
        + "\n\nSe a biblioteca existe mas dá 'Permission denied', o utilizador não"
        + "\nestá no grupo dono de /dev/gpiochip%d (ver 99-gpio.rules)." % chip
    )


def rest_all(gpio: GpioBackend) -> None:
    """Todos os 13 condutores em entrada com pull-up (estado de repouso)."""
    for line in all_lines():
        gpio.input_pullup(line.bcm)


def idle_check(gpio: GpioBackend) -> list[MatrixLine]:
    """Linhas que já estão a 0 V sem ninguém a puxar — curto ou tecla presa."""
    time.sleep(0.05)
    return [line for line in all_lines() if gpio.read(line.bcm) == 0]


def sweep(gpio: GpioBackend, settle_s: float) -> set[tuple[str, str]]:
    """Uma varredura completa: 13 condutores como driver, à vez.

    Devolve os pares (driver, sentida) em que a linha sentida foi arrastada a
    0 V — ou seja, há switch fechado e o díodo conduz NESSE sentido.
    """
    found: set[tuple[str, str]] = set()
    for driver in all_lines():
        gpio.output_low(driver.bcm)
        time.sleep(settle_s)
        for sensed in all_lines():
            if sensed.name == driver.name:
                continue
            if gpio.read(sensed.bcm) == 0:
                found.add((driver.name, sensed.name))
        gpio.input_pullup(driver.bcm)
        time.sleep(settle_s)
    return found


def classify(pair: tuple[str, str]) -> str:
    """'ok' se o par é linha+coluna; senão descreve a anomalia de ligação."""
    driver, sensed = pair
    kinds = {driver[0], sensed[0]}
    if kinds == {"L", "C"}:
        return "ok"
    return "curto entre condutores do mesmo tipo"


def describe_line(line: MatrixLine) -> str:
    return (
        f"{line.name} ({line.net}, GPIO{line.bcm}/pino {line.header_pin}, "
        f"fio {line.wire_color})"
    )


def describe(pair: tuple[str, str]) -> str:
    driver, sensed = pair
    return f"{describe_line(LINES_BY_NAME[driver])}  ->  {describe_line(LINES_BY_NAME[sensed])}"


def grid(pairs: set[tuple[str, str]]) -> str:
    """Grelha 6x7 com X nas posições onde já se viu uma tecla fechar."""
    seen: set[tuple[str, str]] = set()
    for driver, sensed in pairs:
        row = driver if driver[0] == "L" else sensed
        col = sensed if driver[0] == "L" else driver
        if row[0] == "L" and col[0] == "C":
            seen.add((row, col))

    out = ["      " + "  ".join(f"{c:>3}" for c in COL_NAMES)]
    for row in ROW_NAMES:
        cells = ["  X" if (row, col) in seen else "  ." for col in COL_NAMES]
        out.append(f"  {row}  " + "  ".join(f"{c:>3}" for c in cells))
    out.append(f"\n  {len(seen)} de 42 posições vistas (a PCB tem 38 switches).")
    return "\n".join(out)


def report(pairs: set[tuple[str, str]]) -> None:
    print("\n" + "=" * 72)
    if not pairs:
        print("Nenhuma tecla detetada. Ver 'Se não aparecer nada' no fim do ficheiro.")
        print("=" * 72)
        return

    # O sentido só se lê nos pares válidos (linha+coluna); um curto entre dois
    # condutores do mesmo tipo conduz sempre nos dois sentidos e mentiria aqui.
    valid = {p for p in pairs if classify(p) == "ok"}
    row_drives = {d for d, _ in valid if d[0] == "L"}
    col_drives = {d for d, _ in valid if d[0] == "C"}

    print("SENTIDO DA VARREDURA (orientação dos díodos)")
    if row_drives and not col_drives:
        print("  Conduz com a LINHA a 0 V -> o scanner aciona LINHA e lê COLUNA.")
    elif col_drives and not row_drives:
        print("  Conduz com a COLUNA a 0 V -> o scanner aciona COLUNA e lê LINHA.")
    else:
        print("  AMBOS os sentidos conduziram. Ou há díodos montados ao contrário")
        print("  em parte da placa, ou algum díodo está em curto/pontes de solda.")

    both = {p for p in valid if (p[1], p[0]) in valid}
    if both:
        print("\n  Pares que conduzem nos dois sentidos (díodo em curto ou ausente):")
        for pair in sorted(both):
            print(f"    {pair[0]} <-> {pair[1]}")

    bad = {p for p in pairs if classify(p) != "ok"}
    if bad:
        print("\nLIGAÇÕES SUSPEITAS")
        for pair in sorted(bad):
            print(f"  {pair[0]} -> {pair[1]}: {classify(pair)}")

    print("\nMAPA linha x coluna")
    print(grid(pairs))
    print("=" * 72)


def run_scan(gpio: GpioBackend, settle_s: float, stable: int) -> None:
    print("Pinos da matriz com função alternativa (têm de estar desligados no boot):")
    for line in all_lines():
        if line.bcm in SHARED_FUNCTION_PINS:
            print(f"  {line.name}: GPIO{line.bcm} = {SHARED_FUNCTION_PINS[line.bcm]}")
    print()

    rest_all(gpio)
    stuck = idle_check(gpio)
    if stuck:
        print("AVISO — condutores a 0 V em repouso (curto a GND ou tecla presa):")
        for line in stuck:
            print(f"  {describe_line(line)}")
        print("  A varredura vai dar falsos positivos nestes. Resolver primeiro.\n")

    print("A varrer. Prima as teclas UMA A UMA. Ctrl-C termina e imprime o mapa.\n")

    seen_ever: set[tuple[str, str]] = set()
    candidate: set[tuple[str, str]] = set()
    streak = 0
    active: set[tuple[str, str]] = set()

    try:
        while True:
            now = sweep(gpio, settle_s)
            streak = streak + 1 if now == candidate else 0
            candidate = now
            if streak < stable - 1:
                continue
            for pair in sorted(now - active):
                print(f"  tecla  {describe(pair)}")
                seen_ever.add(pair)
            for pair in sorted(active - now):
                print(f"  solta  {pair[0]} -> {pair[1]}")
            active = now
    except KeyboardInterrupt:
        report(seen_ever)


def run_toggle(gpio: GpioBackend, name: str) -> None:
    line = LINES_BY_NAME.get(name)
    if line is None:
        raise SystemExit(f"condutor desconhecido: {name} (use L1..L6, C1..C7)")
    print(f"A piscar {describe_line(line)}")
    print("1 Hz entre 0 V e 3,3 V. Meça com o multímetro na ponta do flat. Ctrl-C para.")
    try:
        while True:
            gpio.output_high(line.bcm)
            time.sleep(0.5)
            gpio.output_low(line.bcm)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--chip", type=int, default=0,
        help="número do gpiochip (0 no Pi 4B; 4 no Pi 5). Padrão: 0",
    )
    parser.add_argument(
        "--settle-us", type=int, default=DEFAULT_SETTLE_US,
        help=f"espera após acionar cada condutor, em µs (padrão {DEFAULT_SETTLE_US})",
    )
    parser.add_argument(
        "--stable", type=int, default=DEFAULT_STABLE,
        help=f"varreduras iguais seguidas para validar (padrão {DEFAULT_STABLE})",
    )
    parser.add_argument(
        "--toggle", metavar="Lx|Cx",
        help="em vez de varrer, pisca um condutor para o localizar no flat",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="imprime a pinagem esperada e sai (não toca no hardware)",
    )
    args = parser.parse_args(argv)

    if args.list:
        for line in all_lines():
            print(describe_line(line))
        return 0

    gpio = open_backend(args.chip)
    print(f"Backend GPIO: {gpio.name} (gpiochip{args.chip})\n")
    try:
        if args.toggle:
            run_toggle(gpio, args.toggle.upper())
        else:
            run_scan(gpio, args.settle_us / 1_000_000, args.stable)
    finally:
        gpio.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
