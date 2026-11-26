"""Display-only formatting: canonical engine tokens rendered as conventional notation.

Purely cosmetic. Never touches the string sent to CalculationEngine; only the
text shown to the user changes. Keep FUNCTION_DISPLAY_SYMBOLS in sync with the
button labels and ctrl_map/shift_map in both fronts (ui/lcd/app.py and
ui/hdmi/app.py) so the symbol shown on a button, in the expression, and spoken
by the TTS always agree.
"""

from __future__ import annotations

import re

from software.core.models import VALUE_KIND_POLAR, VALUE_KIND_RECTANGULAR

FUNCTION_DISPLAY_SYMBOLS: dict[str, str] = {
    "sqrt(": "√(",
    "inv(": "x⁻¹(",
    "logbase(": "log_b(",
    # Convenção Casio, agora coerente com o que o motor faz: Pol(x,y) dá
    # (r,ângulo) e Rec(r,ângulo) dá (x,y). Antes o "Rec(" aqui rotulava a
    # função que fazia justamente o contrário do Rec de uma Casio.
    "polar(": "Pol(",
    "rect(": "Rec(",
    # A tecla EXP é expoente de base dez, e é assim que ela aparece na linha.
    "exp(": "×10^(",
    "asin(": "sen⁻¹(",
    "acos(": "cos⁻¹(",
    "atan(": "tan⁻¹(",
}

_PATTERN = re.compile("|".join(re.escape(token) for token in FUNCTION_DISPLAY_SYMBOLS))


def format_expression_for_display(expression: str) -> str:
    """Render the canonical expression using conventional math notation."""
    return _PATTERN.sub(lambda match: FUNCTION_DISPLAY_SYMBOLS[match.group(0)], expression)


# Rótulo de cada componente de um par, por sentido da conversão. Um par cabia
# numa linha só como "(5, 53.13010235)" - 16 caracteres, acima do limite do
# LCD -, e a truncagem cortava a CABEÇA: o utilizador via "..53.13010235)" e
# perdia o primeiro valor por completo. Daí as duas linhas rotuladas.
PAIR_LABELS: dict[str, tuple[str, str]] = {
    VALUE_KIND_RECTANGULAR: ("x", "y"),
    VALUE_KIND_POLAR: ("r", "θ"),
}


def format_pair_for_display(pair: tuple[float, float], value_kind: str) -> str:
    """Par de coordenadas em DUAS linhas rotuladas ("x = 3" / "y = 4").

    Mesma precisão do resultado escalar (".10g"), para a tela não dizer menos
    do que a voz anuncia.
    """
    first_label, second_label = PAIR_LABELS.get(value_kind, ("x", "y"))
    return (
        f"{first_label} = {pair[0]:.10g}\n"
        f"{second_label} = {pair[1]:.10g}"
    )


def is_pair_result(result) -> bool:
    """True quando o resultado traz um par de coordenadas para exibir."""
    return bool(getattr(result, "ok", False)) and isinstance(
        getattr(result, "value", None), tuple
    ) and bool(getattr(result, "value_kind", None))


def format_result_for_display(result) -> str:
    """Texto do resultado na tela: um par vai em duas linhas, o resto como está."""
    if is_pair_result(result):
        return format_pair_for_display(result.value, result.value_kind)
    return result.display


def clip_display_line(text: str, limit: int) -> str:
    """Corta uma linha longa preservando a CABEÇA.

    Num número a cabeça é o que importa - a ordem de grandeza e os primeiros
    dígitos significativos. Cortar o início (o que esta função substituiu)
    transformava "53364.75335" em "..4.75335", que se lê como outro número.
    """
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 2)] + ".."
