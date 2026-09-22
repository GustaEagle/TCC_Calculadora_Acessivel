"""GPIO assignment of the physical 6x7 keypad matrix on the Pi 4B header (J8).

PRD §6 fixes the keyboard as a Cherry MX hotswap matrix wired straight to the
Raspberry Pi GPIO by a flat cable, with no microcontroller in between, so the
row/column-to-GPIO map IS the keyboard driver's contract: the KiCad schematic
(hardware/pcb/) only names the nets `Row0..Row5` / `Col0..Col6` and leaves the
header end of the flat cable free. This module is the single place where those
nets become pin numbers — and where each switch gets its coordinate and keycap —
so the scanner, the bring-up tool and docs/raspberry-pi-4b/pinout.md can never
disagree about which wire is which.

Numbering: everything is 0-based. The harness label IS the KiCad net (L0 is
Row0, C0 is Col0) and a switch position is written `C#L#`, the way the bench
notes and the scanner's events name it. The switches are `SW0..SW37`; the same
parts are `SW1..SW38` in the KiCad PCB (SWn here = SW(n+1) there).

`bcm` is the Broadcom number, which on the Pi 4 is also the line offset on
`gpiochip0` (see GPIOCHIP_LABEL); `header_pin` is the physical 1..40 position
on J8 and is bench information only — it is never a gpiod offset.

Electrical polarity validated on the hardware (the 1N4148 anode sits on the
switch/column side): the active column is driven HIGH, rows are inputs with
pull-down, idle columns float. The scanner lives in keypad_matrix.py.
"""

from __future__ import annotations

from dataclasses import dataclass

MATRIX_ROWS = 6
MATRIX_COLS = 7


@dataclass(frozen=True)
class MatrixLine:
    """One conductor of the flat cable between the PCB and the J8 header."""

    name: str  # rótulo do chicote = net (L0..L5, C0..C6)
    net: str  # rótulo da net no esquemático KiCad (Row0.., Col0..)
    bcm: int  # numeração Broadcom (gpiozero, libgpiod, overlays)
    header_pin: int  # pino físico no J8, 1..40
    wire_color: str  # cor do fio — é por ela que se confere no hardware


# Colunas: C0..C2 saem em pinos ímpares contíguos (37/35/33), C3/C4 no canto
# par (40/38) e C5/C6 nos pares baixos (10/8), que é como o flat chega à placa.
COL_LINES: tuple[MatrixLine, ...] = (
    MatrixLine("C0", "Col0", 26, 37, "laranja"),
    MatrixLine("C1", "Col1", 19, 35, "roxo"),
    MatrixLine("C2", "Col2", 13, 33, "azul"),
    MatrixLine("C3", "Col3", 21, 40, "preto com final azul"),
    MatrixLine("C4", "Col4", 20, 38, "vermelho"),
    MatrixLine("C5", "Col5", 15, 10, "marrom"),
    MatrixLine("C6", "Col6", 14, 8, "laranja"),
)

# Linhas: L0..L2 nos pinos do SPI0 (19/21/23) e L3..L5 em ímpares contíguos
# (11/13/15). Ordem conferida eletricamente na bancada: uma versão anterior
# desta tabela tinha Row0<->Row2 e Row3<->Row5 trocadas (mesmos GPIOs, ordem
# errada), o que nenhum teste de conjunto apanhava. L3..L5 já estiveram em
# GPIO4/3/2 (pinos 7/5/3) e foram movidas: GPIO2/GPIO3 são o I2C1, o
# barramento que o UPS HAT precisa (0x42, RF-06/RF-14), e têm pull-ups de
# 1,8 kΩ soldados na placa do Pi que nenhuma configuração desliga. Ver
# UPS_I2C_BCM_PINS. Atenção: GPIO27 é o pino físico 13; o pino 27 não é usado.
ROW_LINES: tuple[MatrixLine, ...] = (
    MatrixLine("L0", "Row0", 10, 19, "verde"),
    MatrixLine("L1", "Row1", 9, 21, "branco"),
    MatrixLine("L2", "Row2", 11, 23, "roxo"),
    MatrixLine("L3", "Row3", 17, 11, "roxo"),
    MatrixLine("L4", "Row4", 27, 13, "amarelo"),
    MatrixLine("L5", "Row5", 22, 15, "verde"),
)

ROW_BCM_PINS: tuple[int, ...] = tuple(line.bcm for line in ROW_LINES)
COL_BCM_PINS: tuple[int, ...] = tuple(line.bcm for line in COL_LINES)

# No Pi 4 o controlador de GPIO do header é o gpiochip0 e o offset de cada
# linha nele é o número BCM. Isto NÃO vale noutros SBCs (no Pi 5 o header é
# o RP1, noutro chip), por isso o scanner confere o rótulo antes de supor
# offset == BCM.
GPIOCHIP_PATH = "/dev/gpiochip0"
GPIOCHIP_LABEL = "pinctrl-bcm2711"


@dataclass(frozen=True)
class MatrixSwitch:
    """One key: which switch, where it sits in the grid, what the cap says."""

    switch: str  # SW0..SW37 (= SW1..SW38 no KiCad)
    col: int  # índice em COL_LINES
    row: int  # índice em ROW_LINES
    keycap: str  # texto impresso na tecla — fato de hardware, não token

    @property
    def coord(self) -> str:
        return f"C{self.col}L{self.row}"


def _sw(n: int, col: int, row: int, keycap: str) -> MatrixSwitch:
    return MatrixSwitch(f"SW{n}", col, row, keycap)


# Mapa validado no hardware e conferido contra as nets da PCB
# (hardware/pcb/TCC-09-05-2026: SW(n+1) liga a Col<col> e, pelo díodo, a
# Row<row>). Linha a linha, esquerda (C0..C2) e direita (C3..C6).
SWITCHES: tuple[MatrixSwitch, ...] = (
    _sw(0, 0, 0, "Pol"), _sw(1, 1, 0, "x!"), _sw(2, 2, 0, "Pi"),
    _sw(3, 3, 0, "("), _sw(4, 4, 0, ")"), _sw(5, 5, 0, "%"), _sw(6, 6, 0, "e"),

    _sw(7, 0, 1, "sen"), _sw(8, 1, 1, "cos"),
    _sw(9, 3, 1, "7"), _sw(10, 4, 1, "8"), _sw(11, 5, 1, "9"), _sw(12, 6, 1, "/"),

    _sw(13, 0, 2, "tan"), _sw(14, 1, 2, "log"),
    _sw(15, 3, 2, "4"), _sw(16, 4, 2, "5"), _sw(17, 5, 2, "6"), _sw(18, 6, 2, "*"),

    _sw(19, 0, 3, "x^-1"), _sw(20, 1, 3, "^"),
    _sw(21, 3, 3, "1"), _sw(22, 4, 3, "2"), _sw(23, 5, 3, "3"), _sw(24, 6, 3, "-"),

    # A "?" existe na placa (SW26 no KiCad); só não tem função no software.
    _sw(25, 0, 4, "?"), _sw(26, 1, 4, "nCr"), _sw(27, 2, 4, "√"),
    _sw(28, 3, 4, "0"), _sw(29, 5, 4, ","), _sw(30, 6, 4, "+"),

    _sw(31, 0, 5, "Ctrl"), _sw(32, 1, 5, "exp"), _sw(33, 2, 5, "Shift"),
    _sw(34, 3, 5, "Ans"), _sw(35, 4, 5, "="), _sw(36, 5, 5, "AC"), _sw(37, 6, 5, "Del"),
)

# Posições da grade sem switch montado: sinal aqui é defeito, nunca tecla.
EMPTY_COORDS: frozenset[tuple[int, int]] = frozenset({(2, 1), (2, 2), (2, 3), (4, 4)})

_SWITCH_BY_COORD: dict[tuple[int, int], MatrixSwitch] = {
    (sw.col, sw.row): sw for sw in SWITCHES
}

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


def switch_at(col: int, row: int) -> MatrixSwitch | None:
    """The switch at a grid position (None for the empty positions)."""
    return _SWITCH_BY_COORD.get((col, row))


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


def validate_switch_map(
    switches: tuple[MatrixSwitch, ...],
    empty_coords: frozenset[tuple[int, int]],
) -> None:
    """Refuse a switch map that does not fit the 6x7 grid of the PCB."""
    names = [sw.switch for sw in switches]
    if names != [f"SW{n}" for n in range(len(switches))]:
        raise ValueError(f"switches fora de ordem ou com falhas: {names}")

    coords = [(sw.col, sw.row) for sw in switches]
    if len(set(coords)) != len(coords):
        raise ValueError(f"coordenada repetida no mapa de switches: {sorted(coords)}")

    for sw in switches:
        if not (0 <= sw.col < MATRIX_COLS and 0 <= sw.row < MATRIX_ROWS):
            raise ValueError(f"{sw.switch}: {sw.coord} está fora da grade 7x6")
        if (sw.col, sw.row) in empty_coords:
            raise ValueError(f"{sw.switch}: {sw.coord} é uma posição sem switch")
        if not sw.keycap:
            raise ValueError(f"{sw.switch}: keycap vazio")

    if len(switches) + len(empty_coords) != MATRIX_ROWS * MATRIX_COLS:
        raise ValueError(
            f"{len(switches)} switches + {len(empty_coords)} vazias não cobrem "
            f"as {MATRIX_ROWS * MATRIX_COLS} posições da grade"
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
        if line.bcm in UPS_I2C_BCM_PINS:
            raise ValueError(
                f"{line.name}: GPIO{line.bcm} é do I2C1 reservado ao UPS HAT"
            )

    validate_switch_map(SWITCHES, EMPTY_COORDS)


_validate()
