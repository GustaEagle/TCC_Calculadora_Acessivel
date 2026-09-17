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

    def test_harness_labels_match_the_kicad_nets(self) -> None:
        # L1 é Row0 e C1 é Col0: o chicote é 1-based, o esquemático é 0-based.
        self.assertEqual([line.net for line in pinout.ROW_LINES],
                         [f"Row{i}" for i in range(6)])
        self.assertEqual([line.net for line in pinout.COL_LINES],
                         [f"Col{i}" for i in range(7)])

    def test_wiring_matches_the_bring_up_notes(self) -> None:
        self.assertEqual(pinout.ROW_BCM_PINS, (11, 9, 10, 22, 27, 17))
        self.assertEqual(pinout.COL_BCM_PINS, (26, 19, 13, 21, 20, 15, 14))

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
                "L1": "SPI0 SCLK",
                "L2": "SPI0 MISO",
                "L3": "SPI0 MOSI",
                "L6": "SPI1 CE1 (ALT)",
                "C6": "UART0 RXD",
                "C7": "UART0 TXD",
            },
        )

    def test_i2c1_stays_free_for_the_ups_hat(self) -> None:
        # RF-06/RF-14: o UPS HAT lê a bateria por I2C1 (0x42), e foi por isso
        # que L4..L6 saíram de GPIO4/3/2. Se alguém puser uma linha de volta em
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
