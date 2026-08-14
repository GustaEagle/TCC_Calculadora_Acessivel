"""UI pieces shared by every front-end (LCD panel and external HDMI monitor).

Anything both fronts must agree on lives here so the two never drift apart:
the PRD §13 error text (same code -> same meaning on screen and in speech),
the display-only expression formatting, and the WCAG-verified button palette.
GUI-free on purpose, so all of it stays unit-testable without a Tk runtime.
"""
