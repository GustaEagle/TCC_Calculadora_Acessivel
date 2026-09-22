"""PC keyboard adapter, for development and tests.

The product's own keyboard is the 6x7 matrix read over GPIO
(hw_platform/keypad_matrix.py); both feed the same token handling in the
fronts.
"""

from __future__ import annotations


class KeyboardAdapter:
    """Map local PC keyboard keys to calculator tokens for visual testing."""

    KEY_MAP = {
        # A matriz 6x7 tem uma tecla Ans dedicada; num PC ela não existe, então
        # 'a' ocupa esse lugar para os testes locais. Assim Ctrl + a no PC
        # percorre exatamente o mesmo caminho que Ctrl + Ans no hardware
        # (atalho do histórico).
        "a": "Ans",
        "A": "Ans",
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
