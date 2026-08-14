"""Backwards-compatible re-export: the palette now lives in software/ui_common."""

from software.ui_common.palette import (
    BUTTON_PALETTE,
    DISPLAY_BACKGROUND,
    DISPLAY_FOREGROUND,
    CategoryColors,
)

__all__ = ["BUTTON_PALETTE", "CategoryColors", "DISPLAY_BACKGROUND", "DISPLAY_FOREGROUND"]
