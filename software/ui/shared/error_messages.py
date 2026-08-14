"""User-facing error/warning text, keyed by the PRD §13 code catalogue.

Kept separate from ui/lcd/app.py (which depends on tkinter/ttkbootstrap) so
the mapping and priority-prefix logic are testable without a GUI runtime.
"""

from __future__ import annotations

ERROR_MESSAGES: dict[str, str] = {
    "ERR-001": "Divisão por zero. Limpe ou altere a expressão.",
    "ERR-002": "Argumento inválido para esta função. Verifique o sinal e o domínio.",
    "ERR-003": "Valor fora do domínio da função.",
    "ERR-004": "Parâmetros inválidos para combinação ou permutação.",
    "ERR-005": "Fatorial não definido para este valor.",
    "ERR-006": "Resultado muito grande ou não representável.",
    "ERR-007": "Expressão inválida. Verifique parênteses e operadores.",
    "ERR-008": "Expressão incompleta.",
    "ERR-009": "Dados insuficientes ou inválidos para a conversão.",
    "WRN-010": "Não há resposta anterior.",
}


def spoken_priority_prefix(code: str) -> str:
    """PRD §13: ERR-xxx codes are P1 ("Erro"), WRN-xxx codes are P2 ("Aviso")."""
    return "Erro" if code.startswith("ERR") else "Aviso"


def friendly_message(code: str, fallback: str) -> str:
    return ERROR_MESSAGES.get(code, fallback)
