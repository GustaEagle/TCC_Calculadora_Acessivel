"""Explicit, WCAG-verified color palette for calculator button categories.

ttkbootstrap's built-in bootstyle colors are theme-version-dependent and are
not introspectable without a running Tk instance, so accessibility-critical
categories get an explicit, code-owned palette here instead. Every pair is
verified against WCAG 2.1 AA in software/tests/test_contrast.py (large-text
threshold applies: every label in this UI is >=28pt bold).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryColors:
    background: str
    foreground: str


BUTTON_PALETTE: dict[str, CategoryColors] = {
    "danger": CategoryColors(background="#8C2F26", foreground="#FFFFFF"),   # AC
    "warning": CategoryColors(background="#7A4A00", foreground="#FFFFFF"),  # DEL, operadores, modificadores
    "success": CategoryColors(background="#0B6B45", foreground="#FFFFFF"),  # funções científicas, "="
    "info": CategoryColors(background="#1B5E86", foreground="#FFFFFF"),     # dígitos, Ans
    "primary": CategoryColors(background="#33415C", foreground="#FFFFFF"), # parênteses, %, fallback
}

DISPLAY_BACKGROUND = "#303030"
DISPLAY_FOREGROUND = "#FFFFFF"
