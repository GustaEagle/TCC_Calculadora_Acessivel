"""Conversão de expressões e números para o texto que o TTS fala (pt-BR).

Reúne num só lugar a transformação que a voz precisa, reaproveitando o
vocabulário que já existe em ui/shared/keypad.py (SPOKEN_TOKEN_NAMES /
spoken_token): operadores, funções e símbolos viram as mesmas palavras que o
feedback tecla-a-tecla já usa, e os números decimais ganham o separador falado
"ponto" com a parte fracionária lida dígito a dígito.

Porquê o "ponto": o motor neural (Piper) e o espeak-ng leem "1.2" como "um
dois" - engolindo o separador. Trocar o "." por " ponto " e espaçar os dígitos
da parte decimal ("4 5 6") faz o motor dizer "quatro cinco seis" em vez de
"quatrocentos e cinquenta e seis", preservando TODOS os dígitos (inclusive os
zeros à esquerda/intermediários da parte decimal).

A parte INTEIRA é mantida como dígitos de propósito: o motor já a lê como
cardinal ("123" -> "cento e vinte e três"), então não reimplementamos aqui a
conversão de número por extenso - só corrigimos o separador decimal, que é a
causa real do problema. Notação científica, tuplas e qualquer texto que não
seja um número decimal/inteiro simples são devolvidos intactos, para não
afetar operadores, nomes de função nem a notação científica (§2).
"""

from __future__ import annotations

import re

from software.ui.shared.keypad import SPOKEN_TOKEN_NAMES, spoken_token

# Um literal numérico dentro de uma expressão: "123", "1.2" ou ".5". O sinal
# não entra aqui - numa expressão ele é o operador "-" (um token à parte), e
# num resultado é tratado por spoken_number.
_NUMBER_RE = re.compile(r"\d+\.\d+|\.\d+|\d+")

# Um número isolado (ex.: um resultado), com sinal e parte decimal opcionais.
_DECIMAL_RE = re.compile(r"^(?P<sign>-?)(?P<int>\d*)\.(?P<frac>\d+)$")
_INTEGER_RE = re.compile(r"^(?P<sign>-?)(?P<int>\d+)$")

# Tokens de AÇÃO/atalho (não aparecem numa expressão matemática): ficam de fora
# do casador para nunca serem confundidos com símbolos da expressão. "Ans" NÃO
# entra aqui porque pode, sim, estar na linha de cálculo.
_NON_EXPRESSION_TOKENS = frozenset(
    {"AC", "DEL", "Ctrl", "Shift", "RAD/DEG", "HISTORY", "BLACKOUT", "VOL_UP", "VOL_DOWN"}
)

# Tokens da expressão ordenados do mais longo para o mais curto: assim
# "logbase(" casa antes de "log(", e "exp(" antes de "e".
_EXPRESSION_TOKENS = sorted(
    (token for token in SPOKEN_TOKEN_NAMES if token not in _NON_EXPRESSION_TOKENS),
    key=len,
    reverse=True,
)


def spoken_number(number: str) -> str:
    """Texto falado de UM número (resultado ou literal), com "ponto" no decimal.

    Inteiros e negativos são preservados; o separador decimal vira "ponto" e a
    parte decimal é lida dígito a dígito. Qualquer coisa que não seja um número
    decimal/inteiro simples (notação científica, tupla, texto) volta intacta.
    """
    text = number.strip()
    if not text:
        return text

    decimal = _DECIMAL_RE.match(text)
    if decimal:
        sign = "menos " if decimal.group("sign") else ""
        # ".5" -> "zero ponto cinco": uma parte inteira vazia soa como zero.
        integer_part = decimal.group("int") or "0"
        fraction = " ".join(decimal.group("frac"))  # espaça p/ leitura dígito a dígito
        return f"{sign}{integer_part} ponto {fraction}"

    integer = _INTEGER_RE.match(text)
    if integer:
        sign = "menos " if integer.group("sign") else ""
        return f"{sign}{integer.group('int')}"

    # Não é um número simples (ex.: notação científica "1e+20"): deixa como está.
    return text


def spoken_expression(expression: str) -> str:
    """Texto falado da expressão ATUAL na linha de cálculo (não a avalia).

    Varre a string da esquerda para a direita preservando a ordem: cada número
    vira spoken_number (corrigindo o decimal) e cada operador/função/símbolo
    vira a palavra do catálogo (spoken_token). Uma linha vazia devolve "".
    """
    text = expression.strip()
    if not text:
        return ""

    parts: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue

        number = _NUMBER_RE.match(text, index)
        if number:
            parts.append(spoken_number(number.group()))
            index = number.end()
            continue

        for token in _EXPRESSION_TOKENS:
            if text.startswith(token, index):
                parts.append(spoken_token(token))
                index += len(token)
                break
        else:
            # Símbolo fora do catálogo: fala o próprio caractere (spoken_token
            # devolve o que recebe quando não conhece), sem travar a leitura.
            parts.append(spoken_token(char))
            index += 1

    return " ".join(part for part in parts if part)
