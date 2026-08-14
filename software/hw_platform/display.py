"""Display selection adapter for the LCD panel and the external HDMI monitor.

PRD §7 says the visible output depends on what the Raspberry Pi recognises on
its two HDMI outputs, so the priority rules live here (in hw_platform/) rather
than in any UI package: monitor wins over LCD, and "no usable video" falls back
to audio-only operation (RF-04).

Reading the actual ports depends on OS and driver (still an open item in the
PRD), so detection sits behind HdmiPortReader the same way keyboard.py and
ups.py isolate GPIO/I2C — the simulated reader keeps the app runnable on a
developer machine and makes the §7.4 combinations testable without hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class DisplayMode(str, Enum):
    LCD = "lcd"
    HDMI = "hdmi"
    AUDIO_ONLY = "audio_only"


@dataclass(frozen=True)
class HdmiPorts:
    """Which HDMI outputs currently carry usable video.

    `lcd_connected` is False whenever the LCD cannot show the UI — including
    when the physical switch (PRD §7.0) cut its HDMI output and the panel is in
    standby. Consumers only ever see "usable video: yes/no", never the electrical
    detail behind it.
    """

    lcd_connected: bool
    monitor_connected: bool


class HdmiPortReader(Protocol):
    """Minimal interface DisplaySelector depends on (duck-typed)."""

    def read_ports(self) -> HdmiPorts: ...


class SimulatedHdmiPortReader:
    """Deterministic reader for local development and tests.

    A real implementation (parsing `tvservice`/`xrandr`/`/sys/class/drm`) can
    replace it without touching DisplaySelector — that integration is an open
    item until the hardware tests happen.
    """

    def __init__(
        self,
        lcd_present: bool = True,
        monitor_present: bool = False,
        lcd_switch_on: bool = True,
    ) -> None:
        self.lcd_present = lcd_present
        self.monitor_present = monitor_present
        self.lcd_switch_on = lcd_switch_on

    def read_ports(self) -> HdmiPorts:
        # PRD §7.0: with the switch off the panel is in standby, which for
        # RF-04 purposes is the same as no usable video on the LCD.
        return HdmiPorts(
            lcd_connected=self.lcd_present and self.lcd_switch_on,
            monitor_connected=self.monitor_present,
        )


class DisplaySelector:
    """Resolve the active visual output following the PRD §7.4 flowchart."""

    def __init__(self, port_reader: HdmiPortReader | None = None) -> None:
        self.port_reader = port_reader or SimulatedHdmiPortReader()

    def current_mode(self) -> DisplayMode:
        ports = self.port_reader.read_ports()
        # Monitor takes priority over the LCD whenever both are recognised
        # (§7.2), so the LCD never mirrors the main UI.
        if ports.monitor_connected:
            return DisplayMode.HDMI
        if ports.lcd_connected:
            return DisplayMode.LCD
        return DisplayMode.AUDIO_ONLY
