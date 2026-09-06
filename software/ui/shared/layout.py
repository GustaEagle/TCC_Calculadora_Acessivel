"""Regras de layout do front HDMI: faixa de composição e escala tipográfica.

O monitor externo não tem uma resolução conhecida (PRD §7.2 só diz que ele
existe), então o front decide na construção o que cabe na tela: quais painéis
montar e de que tamanho fica a tipografia. Este módulo concentra essas duas
decisões — e só elas.

Está em ui/shared/ e é deliberadamente livre de Tk: as regras aqui são funções
puras sobre (largura, altura), testáveis sem abrir janela e sem display. Isso
importa porque a suíte já precisa de Xvfb para os testes que instanciam
ttkbootstrap; a lógica de layout não deve engrossar essa fatia.

A decisão é tomada UMA vez, na construção da janela — o front não redimensiona
(ver ui/hdmi/app.py). Numa troca de saída de vídeo (RF-09) o front é
reconstruído, e aí a tela nova é lida naturalmente.
"""

from __future__ import annotations

from enum import Enum

# Resolução em que o layout foi desenhado: as fontes-base abaixo são as que o
# front usava quando o tamanho era fixo, então escala 1.0 reproduz exatamente a
# aparência anterior.
REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720

# Limiar do teclado na tela. O teclado tem 7 colunas (3 à esquerda + 4 à
# direita) e 6 linhas: abaixo disto os botões ficam menores que um alvo de foco
# razoável, e roubam da expressão/resultado o espaço que eles precisam manter.
KEYPAD_MIN_WIDTH = 900
KEYPAD_MIN_HEIGHT = 600

# Limiar do painel de histórico. Ele ocupa ~1/4 da largura útil (weight=1 contra
# weight=3 da calculadora); abaixo disto a coluna fica estreita demais para uma
# entrada como "12 + 34 = 46" caber sem quebrar.
HISTORY_MIN_WIDTH = 1200
HISTORY_MIN_HEIGHT = 700

# Piso e teto da escala. O piso protege o público com visão parcial (PRD §4):
# abaixo disso é melhor truncar mais do que encolher mais. O teto evita que num
# 4K a fonte cresça 3x e sobrem 2 ou 3 botões por linha.
SCALE_FLOOR = 0.75
SCALE_CEILING = 2.0

# Tipografia na resolução de referência (o que o front tinha fixo).
BASE_FONT_SIZES = {
    "expression": 34,
    "result": 58,
    "button": 17,
    "label": 13,
    "history": 14,
}

# Piso absoluto de cada papel, em pontos: abaixo disto o texto deixa de servir
# ao publico com visao parcial (PRD 4), por mais apertada que seja a tela.
# Com SCALE_FLOOR=0.75 nenhum papel chega perto destes valores - o piso e' a
# rede de seguranca para quem, um dia, baixar o SCALE_FLOOR sem medir o efeito
# na legibilidade. Recuperado de ui/shared/responsive.py, removido quando a
# janela passou a ter tamanho fixo.
LEGIBILITY_FLOORS = {
    "expression": 14,
    "result": 20,
    "button": 9,
    "label": 8,
    "history": 8,
}

# Truncamento do display na resolução de referência.
BASE_MAX_EXPRESSION_CHARS = 42
BASE_MAX_RESULT_CHARS = 24


class LayoutTier(str, Enum):
    """Composição escolhida para a tela ativa.

    Ordem de riqueza: COMPACT < MEDIUM < FULL. Só o display é obrigatório —
    teclado e histórico são conveniências: a entrada real é o teclado físico
    (RF-05), então a faixa compacta continua operando todo o catálogo do §5.
    """

    COMPACT = "compact"   # só expressão + resultado
    MEDIUM = "medium"     # + teclado na tela
    FULL = "full"         # + painel de histórico

    @property
    def shows_keypad(self) -> bool:
        return self in (LayoutTier.MEDIUM, LayoutTier.FULL)

    @property
    def shows_history(self) -> bool:
        return self is LayoutTier.FULL


def tier_for(width: int, height: int) -> LayoutTier:
    """Faixa que cabe numa tela de `width`x`height`.

    Exige que AMBOS os eixos atinjam o limiar, em vez de comparar área: uma tela
    1920x480 tem área de sobra e mesmo assim não comporta as 6 linhas de botões.
    """
    if width >= HISTORY_MIN_WIDTH and height >= HISTORY_MIN_HEIGHT:
        return LayoutTier.FULL
    if width >= KEYPAD_MIN_WIDTH and height >= KEYPAD_MIN_HEIGHT:
        return LayoutTier.MEDIUM
    return LayoutTier.COMPACT


def scale_for(width: int, height: int) -> float:
    """Fator de escala tipográfica para uma tela de `width`x`height`.

    Usa o MENOR eixo relativo à referência: escalar pela altura num monitor
    ultrawide agrandaria fontes que a largura não comporta, e vice-versa.
    Uma tela que o Tk não consiga reportar (valores <= 0) cai na referência.
    """
    if width < 1 or height < 1:
        return 1.0
    raw = min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT)
    return max(SCALE_FLOOR, min(SCALE_CEILING, raw))


def font_sizes(scale: float) -> dict[str, int]:
    """Tabela de fontes na escala dada, respeitando o piso de cada papel.

    `scale` 1.0 devolve exatamente a tabela-base (nenhum papel encosta no
    piso nessa escala), entao a aparencia na referencia nao muda.
    """
    return {
        name: max(LEGIBILITY_FLOORS.get(name, 1), round(size * scale))
        for name, size in BASE_FONT_SIZES.items()
    }


def display_limits(width: int, scale: float) -> tuple[int, int]:
    """Quantos caracteres de expressão e de resultado cabem no display.

    Depende da largura E da escala, não só da escala: quantos caracteres cabem
    é (largura da janela) / (largura do caractere), e a largura do caractere
    acompanha a fonte, ou seja, a escala. Num 4K a janela cresce 3x enquanto a
    fonte para no teto de 2x — ali cabe MAIS texto, não menos. Derivar só da
    escala truncaria a expressão justamente na tela mais folgada.
    """
    if width < 1 or scale <= 0:
        return BASE_MAX_EXPRESSION_CHARS, BASE_MAX_RESULT_CHARS
    factor = (width / REFERENCE_WIDTH) / scale
    return (
        max(1, round(BASE_MAX_EXPRESSION_CHARS * factor)),
        max(1, round(BASE_MAX_RESULT_CHARS * factor)),
    )
