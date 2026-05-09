"""Display selection adapter placeholder for LCD and external HDMI."""

from __future__ import annotations

from enum import Enum


class DisplayMode(str, Enum):
    LCD = "lcd"
    HDMI = "hdmi"
    AUDIO_ONLY = "audio_only"


class DisplaySelector:
    """Return the active visual mode.

    The local prototype assumes the LCD-sized UI. On Raspberry Pi this class can
    be replaced with HDMI detection that follows the PRD priority rules.
    """

    def current_mode(self) -> DisplayMode:
        return DisplayMode.LCD
