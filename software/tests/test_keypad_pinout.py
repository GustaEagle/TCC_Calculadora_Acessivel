import re
import unittest
from pathlib import Path

from software.hw_platform import keypad_pinout as pinout

PINOUT_DOC = Path(__file__).resolve().parents[2] / "docs/raspberry-pi-4b/pinout.md"


class KeypadPinoutTest(unittest.TestCase):
    """PRD §6: matriz 6x7 ligada direto ao GPIO, sem MCU — a pinagem é contrato."""

    def test_matrix_has_the_six_rows_and_seven_columns_of_the_pcb(self) -> None:
        self.assertEqual(len(pinout.ROW_LINES), 6)
        self.assertEqual(len(pinout.COL_LINES), 7)

    def test_harness_labels_are_the_kicad_nets(self) -> None:
        # Tudo 0-based: L0 é Row0 e C0 é Col0, sem segunda numeração.
        self.assertEqual([line.net for line in pinout.ROW_LINES],
                         [f"Row{i}" for i in range(6)])
        self.assertEqual([line.name for line in pinout.ROW_LINES],
                         [f"L{i}" for i in range(6)])
        self.assertEqual([line.net for line in pinout.COL_LINES],
                         [f"Col{i}" for i in range(7)])
        self.assertEqual([line.name for line in pinout.COL_LINES],
                         [f"C{i}" for i in range(7)])

    def test_wiring_matches_the_validated_hardware(self) -> None:
        # Ordem conferida na bancada. A tabela antiga tinha Row0<->Row2 e
        # Row3<->Row5 trocadas com os MESMOS GPIOs: só a ordem apanha isso.
        self.assertEqual(pinout.ROW_BCM_PINS, (10, 9, 11, 17, 27, 22))
        self.assertEqual(pinout.COL_BCM_PINS, (26, 19, 13, 21, 20, 15, 14))

    def test_gpio27_is_header_pin_13(self) -> None:
        line = pinout.line_for_bcm(27)
        self.assertEqual((line.name, line.header_pin), ("L4", 13))
        self.assertNotIn(27, [line.header_pin for line in pinout.all_lines()])

    def test_every_line_sits_on_its_documented_header_pin(self) -> None:
        for line in pinout.all_lines():
            with self.subTest(line=line.name):
                self.assertEqual(
                    line.header_pin, pinout.J8_BCM_TO_HEADER_PIN[line.bcm]
                )

    def test_no_gpio_or_header_pin_is_used_twice(self) -> None:
        lines = pinout.all_lines()
        self.assertEqual(len({line.bcm for line in lines}), len(lines))
        self.assertEqual(len({line.header_pin for line in lines}), len(lines))

    def test_every_conductor_is_identified_by_colour(self) -> None:
        # A conferência no hardware é por cor de fio; um rótulo vazio deixaria
        # a documentação inútil na bancada.
        for line in pinout.all_lines():
            with self.subTest(line=line.name):
                self.assertTrue(line.wire_color.strip())

    def test_known_peripheral_conflicts_are_the_expected_ones(self) -> None:
        # Se uma linha mudar de pino e cair sobre outro periférico, este teste
        # falha antes de virar tecla morta no bring-up.
        self.assertEqual(
            {line.name: function for line, function in pinout.peripheral_conflicts()},
            {
                "L2": "SPI0 SCLK",
                "L1": "SPI0 MISO",
                "L0": "SPI0 MOSI",
                "L3": "SPI1 CE1 (ALT)",
                "C5": "UART0 RXD",
                "C6": "UART0 TXD",
            },
        )

    def test_i2c1_stays_free_for_the_ups_hat(self) -> None:
        # RF-06/RF-14: o UPS HAT lê a bateria por I2C1 (0x42), e foi por isso
        # que L3..L5 saíram de GPIO4/3/2. Se alguém puser uma linha de volta em
        # GPIO2/GPIO3, a leitura de bateria morre — este teste falha antes.
        for bcm in pinout.UPS_I2C_BCM_PINS:
            with self.subTest(bcm=bcm):
                self.assertIsNone(pinout.line_for_bcm(bcm))
                self.assertNotIn(bcm, pinout.FREE_BCM_PINS)

    def test_free_pins_exclude_the_matrix_and_the_hat_eeprom(self) -> None:
        used = set(pinout.ROW_BCM_PINS) | set(pinout.COL_BCM_PINS)
        self.assertFalse(used & set(pinout.FREE_BCM_PINS))
        self.assertFalse(set(pinout.HAT_EEPROM_BCM_PINS) & set(pinout.FREE_BCM_PINS))
        self.assertFalse(set(pinout.UPS_I2C_BCM_PINS) & set(pinout.FREE_BCM_PINS))

    def test_matrix_has_room_for_every_switch_on_the_pcb(self) -> None:
        # 38 switches (SW1..SW38) no KiCad cabem na grelha 6x7 = 42 posições.
        self.assertGreaterEqual(pinout.MATRIX_ROWS * pinout.MATRIX_COLS, 38)


class SwitchMapTest(unittest.TestCase):
    """Mapa SW# / C#L# / keycap validado no hardware e conferido na PCB."""

    EXPECTED = {
        "C0L0": "Pol", "C1L0": "x!", "C2L0": "Pi", "C3L0": "(", "C4L0": ")",
        "C5L0": "%", "C6L0": "e",
        "C0L1": "sen", "C1L1": "cos", "C3L1": "7", "C4L1": "8", "C5L1": "9", "C6L1": "/",
        "C0L2": "tan", "C1L2": "log", "C3L2": "4", "C4L2": "5", "C5L2": "6", "C6L2": "*",
        "C0L3": "x^-1", "C1L3": "^", "C3L3": "1", "C4L3": "2", "C5L3": "3", "C6L3": "-",
        "C0L4": "?", "C1L4": "nCr", "C2L4": "√", "C3L4": "0", "C5L4": ",", "C6L4": "+",
        "C0L5": "Ctrl", "C1L5": "exp", "C2L5": "Shift", "C3L5": "Ans", "C4L5": "=",
        "C5L5": "AC", "C6L5": "Del",
    }

    def test_every_switch_has_its_validated_keycap(self) -> None:
        self.assertEqual({sw.coord: sw.keycap for sw in pinout.SWITCHES}, self.EXPECTED)

    def test_switches_are_numbered_in_reading_order(self) -> None:
        self.assertEqual([sw.switch for sw in pinout.SWITCHES],
                         [f"SW{n}" for n in range(38)])
        self.assertEqual(pinout.SWITCHES[9].coord, "C3L1")
        self.assertEqual(pinout.SWITCHES[25].keycap, "?")
        self.assertEqual(pinout.SWITCHES[37].coord, "C6L5")

    def test_empty_positions_have_no_switch(self) -> None:
        self.assertEqual(pinout.EMPTY_COORDS, {(2, 1), (2, 2), (2, 3), (4, 4)})
        for col, row in pinout.EMPTY_COORDS:
            with self.subTest(coord=f"C{col}L{row}"):
                self.assertIsNone(pinout.switch_at(col, row))

    def test_switch_at_finds_the_key(self) -> None:
        sw = pinout.switch_at(3, 1)
        self.assertEqual((sw.switch, sw.keycap), ("SW9", "7"))

    def test_repeated_coordinate_is_refused(self) -> None:
        broken = pinout.SWITCHES[:1] + (pinout.MatrixSwitch("SW1", 0, 0, "x!"),)
        with self.assertRaises(ValueError):
            pinout.validate_switch_map(broken, pinout.EMPTY_COORDS)

    def test_switch_on_an_empty_position_is_refused(self) -> None:
        broken = pinout.SWITCHES[:-1] + (pinout.MatrixSwitch("SW37", 2, 1, "Del"),)
        with self.assertRaises(ValueError):
            pinout.validate_switch_map(broken, pinout.EMPTY_COORDS)

    def test_switch_outside_the_grid_is_refused(self) -> None:
        broken = pinout.SWITCHES[:-1] + (pinout.MatrixSwitch("SW37", 7, 5, "Del"),)
        with self.assertRaises(ValueError):
            pinout.validate_switch_map(broken, pinout.EMPTY_COORDS)


class PinoutDocumentationTest(unittest.TestCase):
    """As tabelas do §6 do pinout.md têm de bater com o módulo.

    A pinagem é conferida na bancada pelo documento, não pelo código: se os
    dois divergirem, alguém solda o fio errado. Este teste lê o markdown e
    compara linha a linha em vez de confiar em revisão manual.
    """

    def _rows_of_table(self, heading: str) -> list[tuple[str, int, int]]:
        text = PINOUT_DOC.read_text(encoding="utf-8")
        table = text.split(heading, 1)[1].split("###", 1)[0]
        found = []
        for line in table.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 5 or not cells[0].startswith("**"):
                continue
            found.append((cells[0].strip("*"), int(cells[3]), int(cells[4])))
        return found

    def test_documented_columns_match_the_module(self) -> None:
        self.assertEqual(
            self._rows_of_table("### 6.1 Colunas"),
            [(line.name, line.bcm, line.header_pin) for line in pinout.COL_LINES],
        )

    def test_documented_rows_match_the_module(self) -> None:
        self.assertEqual(
            self._rows_of_table("### 6.2 Linhas"),
            [(line.name, line.bcm, line.header_pin) for line in pinout.ROW_LINES],
        )

    def test_documented_free_pins_match_the_module(self) -> None:
        text = PINOUT_DOC.read_text(encoding="utf-8")
        listed = re.search(r"\*\*BCM:\*\* ([0-9, ]+)", text).group(1)
        self.assertEqual(
            tuple(int(n) for n in listed.split(",")), pinout.FREE_BCM_PINS
        )


if __name__ == "__main__":
    unittest.main()
