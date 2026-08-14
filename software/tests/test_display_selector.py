import unittest

from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    HdmiPorts,
    SimulatedHdmiPortReader,
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


if __name__ == "__main__":
    unittest.main()
