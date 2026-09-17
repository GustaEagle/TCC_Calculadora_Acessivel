"""GPIO assignment of the physical 6x7 keypad matrix on the Pi 4B header (J8).

PRD §6 fixes the keyboard as a Cherry MX hotswap matrix wired straight to the
Raspberry Pi GPIO by a flat cable, with no microcontroller in between, so the
row/column-to-GPIO map IS the keyboard driver's contract: the KiCad schematic
(hardware/pcb/) only names the nets `Row0..Row5` / `Col0..Col6` and leaves the
header end of the flat cable free. This module is the single place where those
nets become pin numbers, so the scanner, the bring-up checklist and
docs/raspberry-pi-4b/pinout.md can never disagree about which wire is which.

Numbering: the wiring notes label the harness 1-based (L1..L6, C1..C7) while
the schematic nets are 0-based (Row0.., Col0..). L1 is Row0, C1 is Col0, and
both labels travel together in `MatrixLine` so a bring-up session can be done
with either sheet in hand. `bcm` is the Broadcom number used by gpiozero /
libgpiod; `header_pin` is the physical 1..40 position on J8.
"""

from __future__ import annotations

from dataclasses import dataclass

MATRIX_ROWS = 6
MATRIX_COLS = 7


@dataclass(frozen=True)
class MatrixLine:
    """One conductor of the flat cable between the PCB and the J8 header."""

    name: str  # rótulo do chicote (L1..L6, C1..C7)
    net: str  # rótulo da net no esquemático KiCad (Row0.., Col0..)
    bcm: int  # numeração Broadcom (gpiozero, libgpiod, overlays)
    header_pin: int  # pino físico no J8, 1..40
    wire_color: str  # cor do fio — é por ela que se confere no hardware


# Colunas: C1..C3 saem em pinos ímpares contíguos (37/35/33), C4/C5 no canto
# par (40/38) e C6/C7 nos pares baixos (10/8), que é como o flat chega à placa.
COL_LINES: tuple[MatrixLine, ...] = (
    MatrixLine("C1", "Col0", 26, 37, "roxo"),
    MatrixLine("C2", "Col1", 19, 35, "branco"),
    MatrixLine("C3", "Col2", 13, 33, "verde"),
    MatrixLine("C4", "Col3", 21, 40, "preto/azul"),
    MatrixLine("C5", "Col4", 20, 38, "vermelho"),
    MatrixLine("C6", "Col5", 15, 10, "marrom"),
    MatrixLine("C7", "Col6", 14, 8, "laranja"),
)

# Linhas: L1..L3 nos pinos do SPI0 (23/21/19) e L4..L6 em ímpares contíguos
# (15/13/11). L4..L6 estiveram em GPIO4/3/2 (pinos 7/5/3) numa versão anterior
# do chicote e foram movidas: GPIO2/GPIO3 são o I2C1, o barramento que o UPS
# HAT precisa (0x42, RF-06/RF-14), e têm pull-ups de 1,8 kΩ soldados na placa
# do Pi que nenhuma configuração desliga. Ver UPS_I2C_BCM_PINS.
ROW_LINES: tuple[MatrixLine, ...] = (
    MatrixLine("L1", "Row0", 11, 23, "verde"),
    MatrixLine("L2", "Row1", 9, 21, "amarelo"),
    MatrixLine("L3", "Row2", 10, 19, "roxo"),
    MatrixLine("L4", "Row3", 22, 15, "laranja"),
    MatrixLine("L5", "Row4", 27, 13, "marrom"),
    MatrixLine("L6", "Row5", 17, 11, "azul"),
)

ROW_BCM_PINS: tuple[int, ...] = tuple(line.bcm for line in ROW_LINES)
COL_BCM_PINS: tuple[int, ...] = tuple(line.bcm for line in COL_LINES)

# Pinos GPIO do header J8 do Pi 4B (BCM -> pino físico). Serve de tabela de
# conferência: se alguém reatribuir uma linha e trocar BCM/pino, a validação
# no fim do módulo recusa a importação em vez de deixar o erro aparecer só no
# bring-up. Fonte: docs/raspberry-pi-4b/pinout.md §3.
J8_BCM_TO_HEADER_PIN: dict[int, int] = {
    2: 3, 3: 5, 4: 7, 5: 29, 6: 31, 7: 26, 8: 24, 9: 21, 10: 19, 11: 23,
    12: 32, 13: 33, 14: 8, 15: 10, 16: 36, 17: 11, 18: 12, 19: 35, 20: 38,
    21: 40, 22: 15, 23: 16, 24: 18, 25: 22, 26: 37, 27: 13, 0: 27, 1: 28,
}

# Pinos desta pinagem que o firmware pode reclamar para um periférico. Enquanto
# a interface correspondente ficar DESLIGADA no boot (ver
# system/rpi-os/alpine/overlay/boot/usercfg.txt), o pino é GPIO comum e a
# matriz funciona; se alguém ligar a interface, a linha morre em silêncio.
SHARED_FUNCTION_PINS: dict[int, str] = {
    14: "UART0 TXD",
    15: "UART0 RXD",
    11: "SPI0 SCLK",
    9: "SPI0 MISO",
    10: "SPI0 MOSI",
    # SPI1 só existe depois de um overlay explícito (spi1-*cs), que este projeto
    # não usa; fica listado para a tabela de conflitos não mentir por omissão.
    17: "SPI1 CE1 (ALT)",
}

# I2C1 (GPIO2 SDA / GPIO3 SCL, pinos 3 e 5): DELIBERADAMENTE fora da matriz.
# É o barramento onde o UPS HAT lê a bateria (0x42, PRD §12, RF-06/RF-14), e
# são os únicos pinos do header com pull-ups de 1,8 kΩ soldados — bons para
# I2C, maus para linha de matriz (ver docs/raspberry-pi-4b/pinout.md §6.3).
# Nenhuma linha nova deve ocupá-los sem reabrir a decisão do UPS.
UPS_I2C_BCM_PINS: tuple[int, ...] = (2, 3)

# GPIO0/GPIO1 (pinos 27/28) são o I2C de identificação de HAT (EEPROM) e não
# entram na lista de livres: são reservados a qualquer placa que use esse bus
# de identificação (docs/raspberry-pi-4b/pinout.md §5).
HAT_EEPROM_BCM_PINS: tuple[int, ...] = (0, 1)

# GPIO do header disponíveis para sinais futuros: fora a matriz, a EEPROM de
# HAT e os dois pinos reservados ao I2C1 do UPS.
FREE_BCM_PINS: tuple[int, ...] = tuple(
    sorted(
        set(J8_BCM_TO_HEADER_PIN)
        - set(ROW_BCM_PINS)
        - set(COL_BCM_PINS)
        - set(HAT_EEPROM_BCM_PINS)
        - set(UPS_I2C_BCM_PINS)
    )
)


def all_lines() -> tuple[MatrixLine, ...]:
    """Every conductor of the harness, rows first."""
    return ROW_LINES + COL_LINES


def line_for_bcm(bcm: int) -> MatrixLine | None:
    """Which row/column sits on a BCM pin (None if the pin is free)."""
    for line in all_lines():
        if line.bcm == bcm:
            return line
    return None


def peripheral_conflicts() -> tuple[tuple[MatrixLine, str], ...]:
    """Lines parked on a pin with an alternate peripheral function.

    Used by the bring-up checklist and by the tests: the set is expected to be
    stable, so a silent change of pinout that lands a line on top of another
    peripheral shows up as a failing test instead of a dead key.
    """
    return tuple(
        (line, SHARED_FUNCTION_PINS[line.bcm])
        for line in all_lines()
        if line.bcm in SHARED_FUNCTION_PINS
    )


def _validate() -> None:
    lines = all_lines()
    if len(ROW_LINES) != MATRIX_ROWS or len(COL_LINES) != MATRIX_COLS:
        raise ValueError("a matriz do TCC é 6x7: 6 linhas e 7 colunas")

    bcm_pins = [line.bcm for line in lines]
    if len(set(bcm_pins)) != len(bcm_pins):
        raise ValueError(f"GPIO repetido na matriz: {sorted(bcm_pins)}")

    header_pins = [line.header_pin for line in lines]
    if len(set(header_pins)) != len(header_pins):
        raise ValueError(f"pino físico repetido na matriz: {sorted(header_pins)}")

    for line in lines:
        expected = J8_BCM_TO_HEADER_PIN.get(line.bcm)
        if expected is None:
            raise ValueError(f"{line.name}: GPIO{line.bcm} não é GPIO do header J8")
        if expected != line.header_pin:
            raise ValueError(
                f"{line.name}: GPIO{line.bcm} está no pino {expected} do J8, "
                f"não no {line.header_pin}"
            )


_validate()
