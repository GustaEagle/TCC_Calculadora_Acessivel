"""Backwards-compatible re-export: the formatting now lives in software/ui_common."""

from software.ui_common.formatting import (
    FUNCTION_DISPLAY_SYMBOLS,
    format_expression_for_display,
)

__all__ = ["FUNCTION_DISPLAY_SYMBOLS", "format_expression_for_display"]
