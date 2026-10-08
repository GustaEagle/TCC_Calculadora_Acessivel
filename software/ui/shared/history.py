"""Seleção das entradas de histórico mostradas/anunciadas pelos fronts.

CalculatorState.history guarda TODO resultado avaliado, inclusive os que
falharam - o que é correto para o núcleo, mas não é o que alguém espera de um
"histórico de operações": anunciar "um dividido por zero igual a ERR-001" por
voz confunde em vez de ajudar. O filtro fica aqui, compartilhado, para os dois
fronts mostrarem e falarem exatamente as mesmas entradas.
"""

from __future__ import annotations

from typing import Sequence

from software.ui.shared.speech_text import spoken_expression, spoken_number


def recent_entries(history: Sequence, limit: int) -> list:
    """Últimos cálculos BEM-SUCEDIDOS, do mais recente para o mais antigo."""
    successful = [result for result in history if result.ok]
    return list(reversed(successful))[:limit]


def spoken_history(entries: Sequence) -> str:
    """Frase única anunciada por voz para as entradas já selecionadas.

    Expressão e valor passam pela mesma conversão falada dos fronts, para os
    decimais serem lidos com "ponto" aqui também (§2) - sem isto o histórico
    diria "um dois igual a zero cinco" em vez de "um ponto dois...".
    """
    if not entries:
        return "Histórico vazio. Nenhuma operação realizada."
    itens = ". ".join(
        f"{spoken_expression(entry.expression)} igual a {spoken_number(entry.display)}"
        for entry in entries
    )
    return f"Histórico. {len(entries)} operações. {itens}"
