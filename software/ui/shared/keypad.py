"""Keypad definition and spoken names shared by every front-end.

The button *set* is the same on the LCD and on the external monitor (PRD §5
fixes the catalogue of operations); only the arrangement/sizing differs per
front. Keeping the tokens and their spoken names here means a label, the
symbol pushed into the expression, and the TTS announcement can never drift
apart between the two UIs.

Each entry is (label, primary, ctrl_secondary, shift_alternative); None means
the modifier has no alternative for that key, and an empty label is a spacer.
"""

from __future__ import annotations

KeypadRow = list[tuple[str, str, str | None, str | None]]

LEFT_BUTTONS: list[KeypadRow] = [
    [("Pol", "polar(", "rect(", None), ("x!", "!", None, None), ("Pi", "π", "e", None)],
    [("sen", "sen(", "asin(", None), ("cos", "cos(", "acos(", None), ("", "", None, None)],
    [("tan", "tan(", "atan(", None), ("log", "log(", "ln(", "logbase("), ("", "", None, None)],
    [("x⁻¹", "inv(", None, None), ("^", "^", None, None)],
    [("?", "", None, None), ("nCr", "nCr(", "nPr(", None), ("√", "sqrt(", None, None)],
    [("Ctrl", "Ctrl", None, None), ("exp", "exp(", None, None), ("Shift", "Shift", None, None)],
]

RIGHT_BUTTONS: list[KeypadRow] = [
    [("(", "(", None, None), (")", ")", None, None), ("%", "%", None, None), ("e", "e", None, None)],
    [("7", "7", None, None), ("8", "8", None, None), ("9", "9", None, None), ("/", "/", None, "RAD/DEG")],
    [("4", "4", None, None), ("5", "5", None, None), ("6", "6", None, None), ("*", "*", None, None)],
    [("1", "1", None, None), ("2", "2", None, None), ("3", "3", None, None), ("-", "-", None, None)],
    [("0", "0", None, None), (".", ".", None, ","), ("+", "+", None, None)],
    [("Ans", "Ans", "HISTORY", None), ("=", "=", "RECALL", "RECALL"), ("AC", "AC", None, None), ("DEL", "DEL", None, None)],
]

SPOKEN_TOKEN_NAMES: dict[str, str] = {
    "AC": "limpar tudo", "DEL": "apagar", "/": "dividido por", "*": "vezes", "-": "menos", "+": "mais", "^": "elevado a",
    "π": "pi", "e": "é", "(": "abre parênteses", ")": "fecha parênteses", "Ans": "resposta anterior",
    "sen(": "seno", "cos(": "cosseno", "tan(": "tangente", "log(": "logaritmo decimal", "ln(": "logaritmo natural",
    "sqrt(": "raiz quadrada", "asin(": "arco seno", "acos(": "arco cosseno", "atan(": "arco tangente", "!": "fatorial",
    "nCr(": "combinação", "nPr(": "permutação", "polar(": "polar para retangular", "rect(": "retangular para polar",
    "logbase(": "logaritmo na base x", "inv(": "inverso", "exp(": "exponencial", "%": "porcento",
    "x^-1": "inverso", "Ctrl": "controle", "Shift": "shift", ",": "vírgula", ".": "ponto",
    "RAD/DEG": "alternância entre graus e radianos", "HISTORY": "histórico",
}

# O histórico abre por TECLADO (Ctrl + Ans), nunca por um botão dedicado.
# Ans + Ctrl foi escolhido por usar só teclas que existem na matriz 6x7 do
# teclado físico, então o atalho é o mesmo no PC e no hardware do TCC.
HISTORY_TOKEN = "HISTORY"
HISTORY_SHORTCUT_LABEL = "Ctrl + Ans"


# O teclado na tela começa OCULTO nos dois fronts: a entrada real é o teclado
# físico (RF-05), então o padrão é deixar a área livre para expressão e
# resultado. O botão que revela o teclado fica deliberadamente discreto, mas
# continua sendo texto (não só ícone) para ser legível e anunciável.
KEYPAD_SHOW_LABEL = "Mostrar teclado"
KEYPAD_HIDE_LABEL = "Ocultar teclado"
KEYPAD_SHOWN_SPEECH = "Teclado exibido"
KEYPAD_HIDDEN_SPEECH = "Teclado ocultado"


def keypad_toggle_label(controls_visible: bool) -> str:
    """Texto do botão: descreve a AÇÃO, não o estado atual."""
    return KEYPAD_HIDE_LABEL if controls_visible else KEYPAD_SHOW_LABEL


def keypad_toggle_speech(controls_visible: bool) -> str:
    """Anúncio por voz após alternar o teclado."""
    return KEYPAD_SHOWN_SPEECH if controls_visible else KEYPAD_HIDDEN_SPEECH


def spoken_token(token: str) -> str:
    """pt-BR name announced for a token (falls back to the token itself)."""
    return SPOKEN_TOKEN_NAMES.get(token, token)


def button_style(token: str) -> str:
    """Map a token to its palette category (see ui/shared/palette.py)."""
    if token == "AC":
        return "danger"
    if token == "DEL":
        return "warning"
    if token in {"=", "RAD/DEG"}:
        return "success"
    if token in {"Ctrl", "Shift"}:
        return "warning"

    # Operators and other symbols
    if token in {"+", "-", "*", "/", "^", "nCr(", "polar(", "π", ",", "."}:
        return "warning"

    # Scientific functions
    if any(f in token for f in ["sin", "cos", "tan", "log", "sqrt", "!", "asin", "acos", "atan", "inv", "ln", "nPr", "rect"]):
        return "success"

    # Numeric keys
    if token.isdigit() or token == "Ans":
        return "info"

    return "primary"
