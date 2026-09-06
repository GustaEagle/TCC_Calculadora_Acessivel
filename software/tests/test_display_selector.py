import tempfile
import unittest
from pathlib import Path

from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    HdmiPorts,
    SimulatedHdmiPortReader,
    SysfsHdmiPortReader,
    detect_port_reader,
)


class DisplaySelectorTest(unittest.TestCase):
    """PRD §7.4 flowchart: monitor wins, then LCD, then audio-only."""

    def test_monitor_wins_when_both_outputs_are_recognised(self) -> None:
        selector = DisplaySelector(
            SimulatedHdmiPortReader(lcd_present=True, monitor_present=True)
        )
        self.assertEqual(selector.current_mode(), DisplayMode.HDMI)

    def test_lcd_is_used_when_monitor_is_absent(self) -> None:
        selector = DisplaySelector(
            SimulatedHdmiPortReader(lcd_present=True, monitor_present=False)
        )
        self.assertEqual(selector.current_mode(), DisplayMode.LCD)

    def test_audio_only_when_no_output_is_recognised(self) -> None:
        selector = DisplaySelector(
            SimulatedHdmiPortReader(lcd_present=False, monitor_present=False)
        )
        self.assertEqual(selector.current_mode(), DisplayMode.AUDIO_ONLY)

    def test_lcd_switch_off_without_monitor_falls_back_to_audio_only(self) -> None:
        """PRD §7.0: the physical switch puts the panel in standby, which counts
        as no usable video on the LCD (RF-04), not as a working LCD."""
        selector = DisplaySelector(
            SimulatedHdmiPortReader(
                lcd_present=True, monitor_present=False, lcd_switch_on=False
            )
        )
        self.assertEqual(selector.current_mode(), DisplayMode.AUDIO_ONLY)

    def test_lcd_switch_off_still_uses_monitor_when_present(self) -> None:
        selector = DisplaySelector(
            SimulatedHdmiPortReader(
                lcd_present=True, monitor_present=True, lcd_switch_on=False
            )
        )
        self.assertEqual(selector.current_mode(), DisplayMode.HDMI)

    def test_switch_off_reports_lcd_as_disconnected(self) -> None:
        reader = SimulatedHdmiPortReader(lcd_present=True, lcd_switch_on=False)
        self.assertEqual(
            reader.read_ports(), HdmiPorts(lcd_connected=False, monitor_connected=False)
        )

    def test_default_reader_keeps_the_lcd_prototype_behaviour(self) -> None:
        """Running with no reader injected must stay usable on a dev machine."""
        self.assertEqual(DisplaySelector().current_mode(), DisplayMode.LCD)


class SysfsHdmiPortReaderTest(unittest.TestCase):
    """PRD §6: HDMI0 is the LCD, HDMI1 the monitor, read from DRM sysfs."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.drm = Path(self._tmp.name)

    def _connector(self, name: str, status: str, card: str = "card0") -> None:
        """Write a fake /sys/class/drm/<card>-<connector>/status."""
        node = self.drm / f"{card}-{name}"
        node.mkdir(parents=True, exist_ok=True)
        node.joinpath("status").write_text(status + "\n", encoding="utf-8")

    def _reader(self) -> SysfsHdmiPortReader:
        return SysfsHdmiPortReader(
            lcd_connector="HDMI-A-1", monitor_connector="HDMI-A-2", drm_path=self.drm
        )

    def test_reads_both_ports_from_sysfs(self) -> None:
        self._connector("HDMI-A-1", "connected")
        self._connector("HDMI-A-2", "connected")
        self.assertEqual(
            self._reader().read_ports(),
            HdmiPorts(lcd_connected=True, monitor_connected=True),
        )

    def test_disconnected_monitor_leaves_only_the_lcd(self) -> None:
        self._connector("HDMI-A-1", "connected")
        self._connector("HDMI-A-2", "disconnected")
        self.assertEqual(
            DisplaySelector(self._reader()).current_mode(), DisplayMode.LCD
        )

    def test_monitor_on_hdmi1_wins_over_the_lcd(self) -> None:
        self._connector("HDMI-A-1", "connected")
        self._connector("HDMI-A-2", "connected")
        self.assertEqual(
            DisplaySelector(self._reader()).current_mode(), DisplayMode.HDMI
        )

    def test_lcd_switch_cutting_hpd_reads_as_no_usable_video(self) -> None:
        """PRD §7.0: the switch drops hotplug detect, so sysfs says disconnected."""
        self._connector("HDMI-A-1", "disconnected")
        self._connector("HDMI-A-2", "disconnected")
        self.assertEqual(
            DisplaySelector(self._reader()).current_mode(), DisplayMode.AUDIO_ONLY
        )

    def test_unknown_status_is_not_treated_as_usable_video(self) -> None:
        self._connector("HDMI-A-1", "unknown")
        self.assertEqual(
            self._reader().read_ports(),
            HdmiPorts(lcd_connected=False, monitor_connected=False),
        )

    def test_card_number_is_not_hardcoded(self) -> None:
        """The DRM card index varies between boots and driver versions."""
        self._connector("HDMI-A-1", "connected", card="card1")
        self.assertTrue(self._reader().read_ports().lcd_connected)

    def test_missing_connectors_make_the_reader_unavailable(self) -> None:
        self.assertFalse(self._reader().available())

    def test_one_connector_alone_is_not_a_pi(self) -> None:
        """Um notebook tem UMA porta HDMI - e nao pode passar por Raspberry Pi.

        Aceitar "qualquer conector" fazia a maquina de desenvolvimento usar o
        leitor real, que entao nao achava a segunda porta, reportava "sem video
        utilizavel" e abria a calculadora em modo somente audio - sem janela.
        """
        self._connector("HDMI-A-1", "connected")
        self.assertFalse(self._reader().available())

    def test_available_once_both_connectors_exist(self) -> None:
        """O Pi 4B enumera as duas portas HDMI mesmo com uma sem cabo."""
        self._connector("HDMI-A-1", "connected")
        self._connector("HDMI-A-2", "disconnected")
        self.assertTrue(self._reader().available())

    def test_connector_names_can_be_overridden(self) -> None:
        """Bring-up may find HDMI0 under a different DRM name (PRD §11)."""
        self._connector("HDMI-A-3", "connected")
        reader = SysfsHdmiPortReader(
            lcd_connector="HDMI-A-3", monitor_connector="HDMI-A-4", drm_path=self.drm
        )
        self.assertEqual(
            reader.read_ports(), HdmiPorts(lcd_connected=True, monitor_connected=False)
        )

    def test_list_connectors_reports_every_output(self) -> None:
        self._connector("HDMI-A-1", "connected")
        self._connector("HDMI-A-2", "disconnected")
        self.assertEqual(
            self._reader().list_connectors(),
            {"card0-HDMI-A-1": "connected", "card0-HDMI-A-2": "disconnected"},
        )


class DetectPortReaderTest(unittest.TestCase):
    def test_falls_back_to_the_simulated_reader_off_hardware(self) -> None:
        """A dev machine and CI have no Pi HDMI connectors to read."""
        reader = detect_port_reader()
        if not isinstance(reader, SimulatedHdmiPortReader):
            self.assertIsInstance(reader, SysfsHdmiPortReader)
            self.assertTrue(reader.available())


if __name__ == "__main__":
    unittest.main()
