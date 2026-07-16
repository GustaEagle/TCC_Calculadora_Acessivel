"""WCAG 2.1 contrast-ratio utilities used to verify UI color choices.

Pure math, no GUI dependency, so palette decisions can be checked by a fast
unit test instead of eyeballing the rendered app.
"""

from __future__ import annotations

RGB = tuple[int, int, int]

# WCAG 2.1 large text: >=18pt regular or >=14pt bold. Every label in this app
# (buttons at 28pt bold, display at 80/120pt) qualifies as large text.
_NORMAL_TEXT_MIN_RATIO = 4.5
_LARGE_TEXT_MIN_RATIO = 3.0


def hex_to_rgb(hex_color: str) -> RGB:
    hex_color = hex_color.lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _srgb_channel_to_linear(channel: int) -> float:
    value = channel / 255
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: RGB) -> float:
    r, g, b = (_srgb_channel_to_linear(c) for c in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color_a: RGB, color_b: RGB) -> float:
    """WCAG 2.1 contrast ratio, from 1 (no contrast) to 21 (black vs white)."""
    luminance_a = relative_luminance(color_a)
    luminance_b = relative_luminance(color_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def meets_wcag_aa(color_a: RGB, color_b: RGB, *, large_text: bool = False) -> bool:
    threshold = _LARGE_TEXT_MIN_RATIO if large_text else _NORMAL_TEXT_MIN_RATIO
    return contrast_ratio(color_a, color_b) >= threshold
