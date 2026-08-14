"""User interface layer.

Split by output surface (PRD §7): `lcd/` drives the 4.3" Waveshare panel,
`hdmi/` drives the external monitor, and `shared/` holds everything both must
agree on (PRD §13 error text, palette, keypad, formatting, sizing math) so the
two fronts cannot drift apart. Exactly one front runs per session - see
software/app.py.
"""
