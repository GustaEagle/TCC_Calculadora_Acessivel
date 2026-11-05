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

from software.ui.shared.video_blackout import BLACKOUT_TOKEN

KeypadRow = list[tuple[str, str, str | None, str | None]]

LEFT_BUTTONS: list[KeypadRow] = [
    [("Pol", "polar(", "rect(", None), ("x!", "!", None, None), ("Pi", "π", "e", None)],
    [("sen", "sen(", "asin(", None), ("cos", "cos(", "acos(", None), ("", "", None, None)],
    [("tan", "tan(", "atan(", None), ("log", "log(", "ln(", "logbase("), ("", "", None, None)],
    [("x⁻¹", "inv(", None, None), ("^", "^", None, None)],
    # Posição vazia na tela: a tecla "?" existe na matriz (SW25, C0L4) e tem
    # função (consulta de tecla, ver HELP_TOKEN), mas não tem BOTÃO - a consulta
    # é função do teclado físico, e o catálogo do PRD §5 não muda por causa dela.
    # nCr/nPr são INFIXOS: a tecla fica ENTRE os operandos (5 nCr 2), como numa
    # calculadora científica. Os espaços no token são para a linha de cálculo
    # ficar legível; o motor aceita com e sem eles.
    [("", "", None, None), ("nCr", " nCr ", " nPr ", None), ("√", "sqrt(", None, None)],
    # Última linha de modificadores/modo. A tecla EXP saiu daqui: exp( passou a
    # ser a função de Ctrl da tecla "e" (Euler). Isso libertou a tecla de keycap
    # "exp", que passou a ser o Shift, e empurrou o Shift antigo para o "DR"
    # (alterna graus/radianos).
    # Efeito colateral bom: com essa rotação a ordem FÍSICA da linha L5 da
    # matriz (Ctrl, exp->Shift, Shift->DR) passou a coincidir com a ordem destes
    # botões na tela - antes a tela mostrava Ctrl, Shift, DR e o hardware
    # entregava Ctrl, DR, Shift. Ver _KEYCAP_TO_LABEL.
    [("Ctrl", "Ctrl", None, None), ("Shift", "Shift", None, None), ("DR", "RAD/DEG", None, None)],
]

RIGHT_BUTTONS: list[KeypadRow] = [
    # Tecla "e" (Euler): a constante na função principal e a tecla EXP no Ctrl.
    # O EXP é entrada de expoente de BASE DEZ (3 EXP 8 = 3x10^8), não a
    # exponencial de base e - essa sai da PRIMÁRIA desta mesma tecla com o
    # operador de potência ("e ^ 2"). Foi este realojamento que libertou o
    # keycap "exp" para assumir o Shift.
    [("(", "(", None, None), (")", ")", None, None), ("%", "%", None, None), ("e", "e", "exp(", None)],
    [("7", "7", None, None), ("8", "8", None, None), ("9", "9", None, None), ("/", "/", None, "RAD/DEG")],
    [("4", "4", None, None), ("5", "5", None, None), ("6", "6", None, None), ("*", "*", None, None)],
    [("1", "1", None, None), ("2", "2", None, None), ("3", "3", None, None), ("-", "-", "VOL_DOWN", None)],
    # Tecla "." : função principal é o ponto decimal; Shift dá a vírgula (entre
    # argumentos, ex. nCr(5,2)). A alternância DEG/RAD fica no Shift + "/".
    [("0", "0", None, None), (".", ".", None, ","), ("+", "+", "VOL_UP", None)],
    # Shift + Ans lê em voz alta a expressão atual (SPEAK_EXPR); Ctrl + Ans abre
    # o histórico. As duas funções secundárias da MESMA tecla não se atrapalham.
    [("Ans", "Ans", "HISTORY", "SPEAK_EXPR"), ("=", "=", "RECALL", "RECALL"), ("AC", "AC", "BLACKOUT", None), ("DEL", "DEL", None, None)],
]

SPOKEN_TOKEN_NAMES: dict[str, str] = {
    "AC": "limpar tudo", "DEL": "apagar", "/": "dividido por", "*": "vezes", "-": "menos", "+": "mais", "^": "elevado a",
    "π": "pi", "e": "é", "(": "abre parênteses", ")": "fecha parênteses", "Ans": "resposta anterior",
    "sen(": "seno", "cos(": "cosseno", "tan(": "tangente", "log(": "logaritmo decimal", "ln(": "logaritmo natural",
    "sqrt(": "raiz quadrada", "asin(": "arco seno", "acos(": "arco cosseno", "atan(": "arco tangente", "!": "fatorial",
    " nCr ": "combinação", " nPr ": "permutação",
    # Convenção Casio: o nome diz o DESTINO da conversão, que é o que o
    # utilizador escolhe. "Pol" recebe (x,y) e dá (r,ângulo); "Rec" o inverso.
    "polar(": "converter para polar", "rect(": "converter para retangular",
    # A tecla EXP do teclado é entrada de expoente de base DEZ (3 EXP 8 =
    # 3x10^8), não a exponencial de base e - essa fica em "e ^ x".
    "logbase(": "logaritmo na base x", "inv(": "inverso", "exp(": "vezes dez elevado a", "%": "porcento",
    "x^-1": "inverso", "Ctrl": "controle", "Shift": "shift", ",": "vírgula", ".": "ponto",
    "RAD/DEG": "alternância entre graus e radianos", "HISTORY": "histórico",
    "BLACKOUT": "desligar ou religar as telas",
    "VOL_UP": "aumentar volume", "VOL_DOWN": "diminuir volume",
    "SPEAK_EXPR": "ler a expressão atual",
    "HELP": "ajuda",
    # Sem estes dois, a tecla "?" descreveria a tecla "=" lendo o caractere
    # solto e o token RECALL em inglês. Os dígitos não entram aqui de
    # propósito: o motor de voz já os lê como números.
    "=": "calcular", "RECALL": "última resposta",
}

# Shift + Ans: lê em voz alta a expressão que está na linha de cálculo (função
# secundária da tecla Ans). Fica aqui, junto dos outros tokens de atalho, para
# os dois fronts e o pré-cache da voz partilharem o mesmo nome.
SPEAK_EXPRESSION_TOKEN = "SPEAK_EXPR"
SPEAK_EXPRESSION_SHORTCUT_LABEL = "Shift + Ans"

# Volume como função secundária (Ctrl) do "+" e do "-": o modificador é o MESMO
# nas duas teclas e não interfere no uso normal de "+" e "-" como operadores -
# só age quando o Ctrl está ativo, exatamente como os outros atalhos de Ctrl
# (histórico, última resposta, telas). Escolhido Ctrl por ser a família de
# "ações/atalhos do sistema"; o Shift fica livre para entrada alternativa.
VOLUME_UP_TOKEN = "VOL_UP"
VOLUME_DOWN_TOKEN = "VOL_DOWN"
VOLUME_SHORTCUT_LABEL = "Ctrl + +  /  Ctrl + -"

# O histórico abre por TECLADO (Ctrl + Ans), nunca por um botão dedicado.
# Ans + Ctrl foi escolhido por usar só teclas que existem na matriz 6x7 do
# teclado físico, então o atalho é o mesmo no PC e no hardware do TCC.
HISTORY_TOKEN = "HISTORY"
HISTORY_SHORTCUT_LABEL = "Ctrl + Ans"

# Apagar/religar as telas também é Ctrl + tecla existente (a matriz não tem
# tecla livre): Ctrl + AC, que no PC é Ctrl e depois Esc. AC sozinho continua
# limpando - e religa as telas, se estiverem apagadas (video-blackout D4/D5).
BLACKOUT_SHORTCUT_LABEL = "Ctrl + AC"


# A tecla "?" da matriz (SW25, C0L4) é a ÚNICA livre, e é um MODIFICADOR de
# consulta: "o que faz esta tecla?". Pressionar "?" e depois qualquer tecla
# descreve as três funções dessa tecla SEM a executar e sem tocar na expressão.
#
# É um toggle de um só uso, como o Ctrl e o Shift, e não "segurar e pressionar":
# o scanner varre a matriz coluna a coluna e não identifica duas teclas
# pressionadas ao mesmo tempo, então segurar não é opção no hardware do TCC.
#
# Descrever tecla a tecla cobre a descoberta dos atalhos melhor do que a lista
# fixa que esta tecla lia antes: "?" e depois "Ans" diz que o Ctrl abre o
# histórico e o Shift lê a expressão, e o mesmo vale para todas as outras.
HELP_TOKEN = "HELP"
HELP_SHORTCUT_LABEL = "?"
HELP_PROMPT_SPEECH = "Ajuda. Pressione uma tecla."
HELP_CANCELLED_SPEECH = "Ajuda cancelada."
HELP_INDICATOR = "AJUDA"
NO_SECONDARY_SPEECH = "Nenhuma"


def key_description(
    primary: str, secondary: str | None = None, shifted: str | None = None
) -> str:
    """Frase da tecla "?": as três funções da tecla consultada.

    Função pura, para os dois fronts e o modo somente áudio dizerem exactamente
    o mesmo (RF-04/RF-10) e para ser testável sem Tk. Os nomes saem todos de
    SPOKEN_TOKEN_NAMES, então a descrição não pode divergir do que a tecla
    anuncia quando é usada a sério.
    """
    main = spoken_token(primary)
    ctrl = spoken_token(secondary) if secondary else NO_SECONDARY_SPEECH
    shift = spoken_token(shifted) if shifted else NO_SECONDARY_SPEECH
    return (
        f"Função {main}."
        f" Com Controle ativo, função {ctrl}."
        f" Com Shift ativo, função {shift}."
    )


# Teclado físico (matriz 6x7): o keycap é o texto impresso na tecla
# (hw_platform/keypad_pinout.py). Quase todos coincidem com o rótulo do botão
# na tela; estes não. A tecla "," da matriz é a mesma posição do "." na tela: o
# motor usa "." como separador decimal e "," entre argumentos (polar(5,2)), e é
# Shift que dá a vírgula - tal como no botão.
#
# Os modificadores da linha L5 estão ROTACIONADOS em relação ao keycap impresso:
# com exp( realojada no Ctrl da tecla "e", a tecla de keycap "exp" ficou sem
# função e assumiu o Shift, e o keycap "Shift" assumiu o "DR" (graus/radianos).
# Os keycaps impressos ficam portanto desalinhados com a função e precisam de
# ser trocados de posição no hotswap (e reetiquetados em Braille) - a ordem
# FÍSICA resultante, Ctrl / Shift / DR, é a mesma dos botões na tela.
_KEYCAP_TO_LABEL: dict[str, str] = {
    "x^-1": "x⁻¹",
    "Del": "DEL",
    ",": ".",
    "exp": "Shift",
    "Shift": "DR",
}

# Teclas genuinamente desconhecidas (keycap fora do mapa, defeito de hardware)
# continuam a ser anunciadas: sem retorno, quem não vê a tela acharia que a
# tecla está avariada. A "?" já NÃO cai aqui - tem a ajuda.
NO_FUNCTION_SPEECH = "Tecla sem função"

# Teclas da matriz que não têm botão na tela e por isso não são resolvidas por
# varrimento das filas de botões. A "?" é a única: a ajuda é função exclusiva
# do teclado físico.
_KEYCAP_ONLY_TOKENS: dict[str, str] = {"?": HELP_TOKEN}


def entry_for_keycap(keycap: str) -> tuple[str, str | None, str | None] | None:
    """(primary, ctrl_secondary, shift_alternative) for a physical key.

    None only for a keycap outside the map (unknown hardware), never for the
    "?" - that one is the help key.
    """
    keycap_only = _KEYCAP_ONLY_TOKENS.get(keycap)
    if keycap_only is not None:
        return keycap_only, None, None
    label = _KEYCAP_TO_LABEL.get(keycap, keycap)
    for row in LEFT_BUTTONS + RIGHT_BUTTONS:
        for button_label, primary, secondary, shifted in row:
            if button_label and button_label == label:
                return primary, secondary, shifted
    return None


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

    # Operators and other symbols (nCr é infixo, logo é operador aqui)
    if token in {"+", "-", "*", "/", "^", " nCr ", "polar(", "π", ",", "."}:
        return "warning"

    # Scientific functions
    if any(f in token for f in ["sin", "cos", "tan", "log", "sqrt", "!", "asin", "acos", "atan", "inv", "ln", "nPr", "rect"]):
        return "success"

    # Numeric keys
    if token.isdigit() or token == "Ans":
        return "info"

    return "primary"
