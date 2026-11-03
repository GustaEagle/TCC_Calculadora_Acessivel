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


# Códigos ERR-xxx que o §13 classifica como P2. O prefixo do código NÃO decide
# a prioridade sozinho: o ERR-008 (entrada incompleta) é ERR-xxx mas P2, e a
# tabela do §13 manda falá-lo como «Aviso 008. Expressão incompleta.» - dizer
# "Erro" ali exageraria a gravidade para quem só tem o áudio (RF-04/RF-07).
_P2_ERROR_CODES = frozenset({"ERR-008"})


def spoken_priority_prefix(code: str) -> str:
    """PRD §13: "Erro" para os códigos P1, "Aviso" para os P2."""
    if code in _P2_ERROR_CODES or not code.startswith("ERR"):
        return "Aviso"
    return "Erro"


def friendly_message(code: str, fallback: str) -> str:
    return ERROR_MESSAGES.get(code, fallback)
