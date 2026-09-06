"""Display selection adapter for the LCD panel and the external HDMI monitor.

PRD §7 says the visible output depends on what the Raspberry Pi recognises on
its two HDMI outputs, so the priority rules live here (in hw_platform/) rather
than in any UI package: monitor wins over LCD, and "no usable video" falls back
to audio-only operation (RF-04).

Which physical port carries which panel is fixed by the build (PRD §6):
HDMI0 is always the LCD, HDMI1 is always the external monitor. A real reader
therefore identifies each panel by port, not by EDID — but the port-to-DRM
connector names (`HDMI-A-1`/`HDMI-A-2` under vc4-kms-v3d) still have to be
confirmed on the hardware, so detection stays behind HdmiPortReader the same
way keyboard.py and ups.py isolate GPIO/I2C. The simulated reader keeps the app
runnable on a developer machine and makes the §7.4 combinations testable
without hardware.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

# PRD §6 fixes the cabling, so a port is enough to tell the panels apart — no
# EDID parsing needed. The DRM connector names are the part that still varies
# with kernel/driver, so they are constants here and overridable by env var:
# the image can be corrected during bring-up without a code change.
DRM_CLASS_PATH = Path("/sys/class/drm")
DEFAULT_LCD_CONNECTOR = "HDMI-A-1"  # HDMI0 do Pi 4B, a porta junto ao USB-C
DEFAULT_MONITOR_CONNECTOR = "HDMI-A-2"  # HDMI1 do Pi 4B
LCD_CONNECTOR_ENV = "CALC_LCD_CONNECTOR"
MONITOR_CONNECTOR_ENV = "CALC_MONITOR_CONNECTOR"


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

    Used off the Pi, where SysfsHdmiPortReader finds no DRM connectors to read
    (see detect_port_reader), and in tests, to drive the §7.4 combinations
    — including the switch-off case — without hardware.
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


class SysfsHdmiPortReader:
    """Real reader for the Raspberry Pi: DRM connector status from sysfs.

    Each connector exposes `/sys/class/drm/card<N>-<CONNECTOR>/status`, holding
    "connected", "disconnected" or "unknown". The card number changes between
    boots and driver versions, so the connector name is globbed rather than
    hard-coded into a full path.

    The LCD switch (PRD §7.0) needs no separate input here: cutting the HDMI
    line drops hotplug detect, so the panel simply reads as disconnected —
    exactly the "no usable video" RF-04 expects. Confirm on the hardware that
    the switch really opens HPD and not only the panel's power rail; if it
    only kills the backlight, the LCD keeps reading "connected" and this
    reader needs the switch wired as its own GPIO input.
    """

    def __init__(
        self,
        lcd_connector: str | None = None,
        monitor_connector: str | None = None,
        drm_path: Path = DRM_CLASS_PATH,
    ) -> None:
        self.lcd_connector = lcd_connector or os.environ.get(
            LCD_CONNECTOR_ENV, DEFAULT_LCD_CONNECTOR
        )
        self.monitor_connector = monitor_connector or os.environ.get(
            MONITOR_CONNECTOR_ENV, DEFAULT_MONITOR_CONNECTOR
        )
        self.drm_path = drm_path

    def connector_status(self, connector: str) -> str | None:
        """Raw sysfs status, or None when the connector is not present."""
        for path in sorted(self.drm_path.glob(f"card*-{connector}")):
            try:
                return path.joinpath("status").read_text().strip().lower()
            except OSError:
                # A connector can vanish between glob and read (hotplug, or an
                # unreadable node); treat it as one more absent output.
                continue
        return None

    def list_connectors(self) -> dict[str, str]:
        """Every DRM connector and its status — bring-up diagnostic.

        Used to confirm which name the kernel gives HDMI0 and HDMI1 before
        those names are trusted in the image.
        """
        found: dict[str, str] = {}
        for path in sorted(self.drm_path.glob("card*-*")):
            status_file = path.joinpath("status")
            try:
                found[path.name] = status_file.read_text().strip().lower()
            except OSError:
                continue
        return found

    def available(self) -> bool:
        """True when this machine exposes BOTH configured connectors.

        Both, not either: the Pi 4B has two HDMI ports and always enumerates
        both in sysfs (a disconnected one still shows up, with status
        "disconnected"). A developer laptop has a single HDMI port, so
        accepting either one made it look like a Pi - the reader then found the
        second connector missing, reported no usable video, and the calculator
        started in audio-only mode with no window at all.

        Bring-up may find the ports under other DRM names (PRD §11); the
        connector names stay overridable, so this stays a check about how many
        of the CONFIGURED ports exist, not about their spelling.
        """
        return (
            self.connector_status(self.lcd_connector) is not None
            and self.connector_status(self.monitor_connector) is not None
        )

    def read_ports(self) -> HdmiPorts:
        return HdmiPorts(
            lcd_connected=self.connector_status(self.lcd_connector) == "connected",
            monitor_connected=self.connector_status(self.monitor_connector) == "connected",
        )


def detect_port_reader() -> HdmiPortReader:
    """Sysfs reader on the Pi, simulated reader anywhere else.

    Keeps a developer machine on the deterministic stub without needing a
    flag, while the image gets real detection with no extra configuration.
    The test is "both configured connectors exist" rather than "any DRM
    connector exists": a laptop with one HDMI port also has DRM connectors, and
    assuming it was a Pi left the app in audio-only mode with no window.
    """
    sysfs = SysfsHdmiPortReader()
    if sysfs.available():
        return sysfs
    return SimulatedHdmiPortReader()


class DisplaySelector:
    """Resolve the active visual output following the PRD §7.4 flowchart."""

    def __init__(self, port_reader: HdmiPortReader | None = None) -> None:
        # Injected in tests; left to detect_port_reader() otherwise, so the Pi
        # reads real ports and a developer machine keeps the stub.
        self.port_reader = port_reader or detect_port_reader()

    def current_mode(self) -> DisplayMode:
        ports = self.port_reader.read_ports()
        # Monitor takes priority over the LCD whenever both are recognised
        # (§7.2), so the LCD never mirrors the main UI.
        if ports.monitor_connected:
            return DisplayMode.HDMI
        if ports.lcd_connected:
            return DisplayMode.LCD
        return DisplayMode.AUDIO_ONLY


class DisplayWatcher:
    """Notice a video output change while the calculator is already running.

    RF-09: the front must follow the video state without a manual restart, and
    that is the product's normal flow — the LCD is built into the enclosure and
    is always there at boot, so the external monitor is by definition plugged
    in later, with the calculator already on.

    This can only work if the kernel refreshes connector status at runtime.
    Under `vc4-kms-v3d` the DRM driver does update sysfs on hotplug; on the
    legacy firmware path the mode is fixed at boot and nothing in userspace can
    see a monitor that arrived afterwards. The check to settle it on the
    hardware is in system/rpi-os/alpine/README.md.
    """

    def __init__(
        self,
        selector: DisplaySelector | None = None,
        mode: DisplayMode | None = None,
    ) -> None:
        self.selector = selector or DisplaySelector()
        self.mode = mode if mode is not None else self.selector.current_mode()

    def poll(self) -> DisplayMode | None:
        """The new mode when the output changed, None while it is unchanged."""
        current = self.selector.current_mode()
        if current == self.mode:
            return None
        self.mode = current
        return current
