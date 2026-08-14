"""Resolution-independent sizing math for the front-ends.

Kept free of any Tk import so the responsive behaviour is unit-testable at any
resolution on a headless machine (CI has no display, and window managers do not
always honour a programmatic resize). The UI only wires these numbers into
ttk styles; the decisions themselves live here.

Sizes are declared at a reference resolution and scaled from it, so the layout
is defined by proportions instead of fixed pixel dimensions.
"""

from __future__ import annotations

REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720

# Scale bounds keep text legible on small panels without letting a 4K screen
# blow the buttons past the point of being reachable.
MIN_SCALE = 0.55
MAX_SCALE = 2.2

# Degenerate-window guard, not a target resolution.
MIN_USABLE_WIDTH = 640
MIN_USABLE_HEIGHT = 400

# (base size at the reference resolution, absolute floor in points)
FONT_SPECS: dict[str, tuple[int, int]] = {
    "expression": (34, 14),
    "result": (58, 20),
    "button": (17, 9),
    "label": (13, 8),
    "history": (14, 8),
}


def responsive_scale(width: int, height: int) -> float:
    """Scale factor for a window of `width` x `height` pixels.

    Uses the smaller of the two axes so a wide-but-short window shrinks its
    text too, instead of overflowing vertically.
    """
    usable_width = max(width, MIN_USABLE_WIDTH)
    usable_height = max(height, MIN_USABLE_HEIGHT)
    scale = min(usable_width / REFERENCE_WIDTH, usable_height / REFERENCE_HEIGHT)
    return max(MIN_SCALE, min(MAX_SCALE, scale))


def font_sizes(scale: float) -> dict[str, int]:
    """Point sizes for every text role at the given scale."""
    return {
        role: max(floor, int(base * scale))
        for role, (base, floor) in FONT_SPECS.items()
    }


def visible_chars(width: int, font_size: int, column_fraction: float = 0.72) -> int:
    """Roughly how many characters fit on one display line.

    Truncation follows the real window and font rather than the hard-coded
    counts the LCD front uses. Note that because the font scales with the
    window, capacity stays roughly constant across resolutions - a bigger
    screen renders the same text larger, it does not cram more in.
    0.62 approximates the width/height ratio of a digit in the UI font.
    """
    usable_width = max(width, MIN_USABLE_WIDTH) * column_fraction
    per_char = max(1.0, font_size * 0.62)
    return max(8, int(usable_width / per_char))
