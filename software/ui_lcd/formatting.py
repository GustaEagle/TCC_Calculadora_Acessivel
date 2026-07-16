"""Display-only formatting: canonical engine tokens rendered as conventional notation.

Purely cosmetic. Never touches the string sent to CalculationEngine; only the
text shown to the user changes. Keep FUNCTION_DISPLAY_SYMBOLS in sync with the
button labels and ctrl_map/shift_map in ui_lcd/app.py so the symbol shown on a
button, in the expression, and spoken by the TTS always agree.
"""

from __future__ import annotations

import re

FUNCTION_DISPLAY_SYMBOLS: dict[str, str] = {
    "sqrt(": "√(",
    "inv(": "x⁻¹(",
    "logbase(": "log_b(",
    "rect(": "Rec(",
    "asin(": "sen⁻¹(",
    "acos(": "cos⁻¹(",
    "atan(": "tan⁻¹(",
}

_PATTERN = re.compile("|".join(re.escape(token) for token in FUNCTION_DISPLAY_SYMBOLS))


def format_expression_for_display(expression: str) -> str:
    """Render the canonical expression using conventional math notation."""
    return _PATTERN.sub(lambda match: FUNCTION_DISPLAY_SYMBOLS[match.group(0)], expression)
