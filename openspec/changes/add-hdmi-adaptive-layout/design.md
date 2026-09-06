## Context

O front do monitor ([software/ui/hdmi/app.py](../../../software/ui/hdmi/app.py), ~590 linhas) foi escrito com uma propriedade deliberada, declarada no próprio docstring: *"Non-resizable window with font sizes declared once, so the layout is never recomputed at runtime — there is no resize path to get wrong."* A janela adota o tamanho da tela ativa (`winfo_screenwidth/height`) porque o kiosk não tem gerenciador de janelas e o X posiciona tudo em (0,0).

O que **já** acompanha a resolução: a realocação por `grid` com `weight`/`uniform`. O que **não** acompanha: `FONT_SIZES` e `MAX_EXPRESSION_CHARS`/`MAX_RESULT_CHARS`, calibrados para ~1280x720. E a composição é sempre a mesma — histórico fixo na coluna 1, teclado com toggle manual (`controls_visible`).

Restrições que moldam o desenho:

- **Kiosk sem WM:** janela = tela; não há usuário arrastando bordas no produto final.
- **Teclado físico é a entrada real (RF-05):** o teclado na tela é conveniência, não requisito de operação — por isso pode sumir sem quebrar nada.
- **CI headless:** testes que instanciam `ttk.Window` já exigiram Xvfb no workflow. Ampliar essa superfície é caro e frágil.
- **RF-09 (troca de saída):** o front pode ser construído uma **segunda** vez no mesmo processo; qualquer estado de layout tem de ser derivado na construção, nunca global mutável.

## Goals / Non-Goals

**Goals:**

- Fontes, espaçamentos e truncamento derivados da resolução, com piso e teto.
- Três faixas (compacta / média / completa) decididas **uma vez**, na construção.
- Limiares e escala em **um único ponto**, como funções puras testáveis sem display.
- Quando o teclado não é montado, o botão de alternância também não é.

**Non-Goals:**

- Janela redimensionável ou reação a `<Configure>` (decisão explícita do usuário).
- Mudar o front do LCD (resolução fixa pelo painel 4,3").
- Mudar motor, voz, ou a seleção de saída de vídeo.
- Tema/paleta: continuam como estão.

## Decisions

### D1 — Decidir no arranque, mantendo `resizable(False, False)`

A faixa e a escala saem de `winfo_screenwidth()/winfo_screenheight()` na construção e não mudam depois.

- **Por quê:** preserva a propriedade central do arquivo (não há re-layout em runtime) e casa com o kiosk, onde a janela é sempre do tamanho do painel. Numa troca de saída (RF-09) o front é **reconstruído**, então a nova tela é lida naturalmente.
- **Alternativa considerada:** reagir a `<Configure>` com debounce, como a calculadora do Windows. Rejeitada por decisão do usuário: acrescentaria um caminho de código que no produto final nunca executa.
- **Consequência de spec:** o cenário "Redimensionamento manual da janela" descrevia algo que o código nunca fez — a janela sempre foi fixa. Ele sai no delta spec, substituído por "Tamanho fixado na construção".

### D2 — Regra de layout como módulo puro, sem Tk

Novo `software/ui/shared/layout.py` com apenas dados e funções puras:

```
REFERENCE_WIDTH, REFERENCE_HEIGHT = 1280, 720
KEYPAD_MIN_WIDTH,  KEYPAD_MIN_HEIGHT  =  900, 600
HISTORY_MIN_WIDTH, HISTORY_MIN_HEIGHT = 1200, 700
SCALE_FLOOR, SCALE_CEILING = 0.75, 2.0

class LayoutTier(str, Enum): COMPACT / MEDIUM / FULL
def tier_for(width, height) -> LayoutTier
def scale_for(width, height) -> float
def font_sizes(scale) -> dict[str, int]
def display_limits(width, scale) -> tuple[int, int]
```

- **Por quê:** é o que torna o comportamento testável **sem abrir janela** — o CI headless já custou uma correção (Xvfb + `python3-tk`); a regra nova não deve depender disso. Também atende à exigência do spec de limiares num ponto só.
- **Alternativa:** métodos privados dentro de `CalculatorApp`. Rejeitada: só testáveis instanciando a janela.

### D3 — Faixas por **largura E altura**, não por área

`tier_for` exige que **ambas** as dimensões atinjam o limiar. Uma tela 1920x480 (larga e baixa) tem área de sobra mas não tem altura para 6 linhas de botões.

Limiares e a razão de cada número:

| Faixa | Limiar | Origem |
| --- | --- | --- |
| completa | ≥ 1200x700 | histórico ocupa ~1/4 da largura útil (`weight=1` contra `weight=3`); abaixo disso o painel fica estreito demais para "12 + 34 = 46" numa linha |
| média | ≥ 900x600 | teclado tem **7 colunas** (3 à esquerda + 4 à direita) e 6 linhas; abaixo disso os botões ficam menores que um alvo de toque/foco razoável |
| compacta | resto | só display |

São **pontos de partida calibrados pela composição atual**, a confirmar no hardware (tarefa de validação): o critério é legibilidade, não o número em si.

### D4 — Escala pelo menor eixo, com piso e teto

`scale = clamp(min(width/1280, height/720), 0.75, 2.0)`.

- **Menor eixo:** escalar pela altura num monitor ultrawide agrandaria fontes que a largura não comporta (e vice-versa).
- **Piso 0,75:** abaixo disso o texto deixaria de servir ao público com visão parcial (PRD §4) — melhor truncar mais do que encolher mais.
- **Teto 2,0:** num 4K, escalar 3x deixaria 2 ou 3 botões por linha; 2x já dá tipografia confortável.
- `font_sizes(scale)` multiplica a tabela atual (que passa a ser a *base* de 1280x720) e arredonda. Já `display_limits(width, scale)` precisa da **largura além da escala**: quantos caracteres cabem é (largura da janela)/(largura do caractere), e a largura do caractere acompanha a escala — logo o fator é `(width/1280)/scale`. Derivar só da escala erraria justamente no 4K, onde a janela cresce 3x enquanto a fonte para no teto de 2x: caberia *mais* texto (63 caracteres), não menos.

### D5 — Faixa omite o painel: não monta, não reserva

Nas faixas abaixo do limiar, os widgets **não são criados** (em vez de criados e escondidos com `grid_remove`).

- **Por quê:** um widget escondido continua no `grid` do pai, ainda participa da travessia por Tab dependendo do estado, e mantém a coluna de histórico com peso reservado — o spec exige que nenhuma área vazia fique no lugar. Não criar é mais simples e mais barato.
- **Efeito no toggle:** `controls_visible` só existe como escolha do usuário na faixa que tem teclado. Sem teclado, o rodapé não recebe o botão e `_set_initial_focus` cai no que existir.
- **Cuidado:** `_update_keypad_labels()` e `_apply_controls_visibility()` iteram sobre `self.buttons`, que fica **vazio** na faixa compacta — os dois precisam tolerar isso sem erro.

### D6 — Medir a tela pelo `xrandr`, não pelo valor que o Tk devolve

`winfo_screenwidth()`/`winfo_screenheight()` leem a struct `Screen` do Xlib, preenchida **quando a conexão com o X é aberta** e **não** atualizada quando o RandR redimensiona a tela. O front passa a perguntar ao `xrandr` (`video_output.screen_size()`, que parseia `Screen 0: ... current W x H`) e só cai no Tk quando não há X/xrandr — fora do Pi, onde nada redimensionou e o valor do Tk está certo.

- **Por quê:** é o caso normal do produto, não uma exceção. O monitor externo é **sempre** ligado com a calculadora já em uso (RF-09), então este front nasce logo depois de o `xrandr` trocar de painel — exatamente quando o valor do Tk ainda é o do LCD. Confiar nele fazia a janela subir com 800x480 e, portanto, na **faixa compacta**: sem teclado e sem histórico, num monitor grande.
- **Sintoma que originou a decisão:** relatado no hardware — "iniciou no tamanho mínimo".
- **Consequência de teste:** `test_window_geometry` codificava "o front pergunta ao Tk"; o contrato mudou de fonte (a intenção — medir em vez de assumir — continua), então os testes passam a simular as duas fontes.
- **Custo:** um `xrandr --query` por construção de front. A leitura é feita **uma vez** e reaproveitada pela geometria e pelo layout.

## Risks / Trade-offs

- **[Limiares errados no hardware real]** → São constantes nomeadas num módulo só; ajustar é trocar um número. A validação no monitor do TCC fecha isso.
- **[Faixa compacta parecer "quebrada" a quem não sabe]** → O teclado físico continua operando tudo (RF-05) e a voz não muda; ainda assim, vale confirmar no hardware se a ausência do teclado confunde.
- **[Escala e truncamento discordarem]** → `MAX_*_CHARS` é uma aproximação de quantos caracteres cabem; com fonte proporcional (Segoe UI) não é exato. Mitigação: derivar do mesmo `scale` que dimensiona a fonte, e conferir visualmente nas três faixas.
- **[Regressão no front completo]** → Com escala 1.0 (1280x720) os números devem cair **exatamente** nos valores atuais. Isso vira teste: `font_sizes(1.0) == FONT_SIZES` de hoje.
- **[Segunda construção na troca de saída (RF-09)]** → Como tudo é derivado na construção e nada fica em variável de módulo, a reconstrução lê a tela nova. Sem estado global novo.

## Migration Plan

- Additivo e local ao front HDMI; sem migração de dados nem mudança de interface pública.
- Ordem: módulo puro + testes → consumir no front → validar as três faixas.
- **Como validar sem três monitores:** `make run-hdmi` num PC força o front; para simular faixas sem hardware, o Tk reporta a tela real, então a verificação de faixa/escala fica nos testes puros, e a inspeção visual usa as resoluções disponíveis (o monitor do TCC e o LCD do Pi).
- Rollback: reverter o commit; nada persiste fora do processo.

## Open Questions

- Os limiares 900x600 / 1200x700 sobrevivem ao monitor real do TCC, ou o histórico ainda fica apertado em 1200?
- Na faixa compacta, vale **anunciar por voz** ao abrir que o teclado na tela não está disponível nessa resolução, ou isso é ruído (já que o teclado físico é a entrada normal)?
- O piso 0,75 é suficiente para o pior monitor previsto (1024x768), ou a faixa compacta deve começar antes?
