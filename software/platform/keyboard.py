"""Keyboard adapter placeholder for the future GPIO 7x7 matrix."""

from __future__ import annotations


class KeyboardAdapter:
    """Map local PC keyboard keys to calculator tokens for visual testing."""

    KEY_MAP = {
        ",": ",",
        "x": "*",
        "X": "*",
        "*": "*",
        "/": "/",
        "+": "+",
        "-": "-",
        "^": "^",
        ".": ".",
        "(": "(",
        ")": ")",
    }

    def map_key(self, key: str) -> str | None:
        if key.isdigit():
            return key
        return self.KEY_MAP.get(key)
