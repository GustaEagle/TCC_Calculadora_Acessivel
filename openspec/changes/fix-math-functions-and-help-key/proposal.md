## Why

Quatro operações que o **PRD §5** declara como catálogo fechado da calculadora não funcionam pelo teclado físico, e uma tecla da matriz 6x7 continua sem função. Como o produto é operado por quem **não vê a tela** (RF-04, RF-10), uma função que falha ou uma tecla muda não são defeitos cosméticos: são a única via de acesso àquela operação.

Diagnóstico no código atual (`software/core/engine.py`):

- **Parênteses não fechados abortam o cálculo.** `_normalize()` nunca equilibra os parênteses, então o texto vai direto para `ast.parse()` e a expressão `sqrt(144` morre em `ERR-007` (`'(' was never closed`). Numa calculadora científica física isso é o caso **normal**, não a exceção: o utilizador pressiona `√`, `1`, `4`, `4`, `=` e nunca pressiona o fecho. Com a matriz 6x7, fechar parênteses exige localizar a tecla `)` — custo de navegação que não existiria se o fecho inequívoco fosse implícito.
- **A combinação é inalcançável pelo teclado.** O motor só aceita a forma funcional `nCr(5,2)`, mas a tecla `nCr` insere o token `nCr(` ([`ui/shared/keypad.py:24`](../../../software/ui/shared/keypad.py)). Pressionar a sequência natural `5`, `nCr`, `2` constrói a string `5nCr(2`, que falha em `ERR-007` (`invalid decimal literal`). Para obter `nCr(5,2)` o utilizador teria de pressionar a função **antes** dos operandos e ainda produzir a vírgula por `Shift` + `.` — ordem que nenhuma calculadora científica usa e que ninguém descobre sem ver a tela. Resultado prático: `nCr` e `nPr` estão no catálogo §5 mas inacessíveis no produto.
- **As conversões de coordenadas descartam metade do resultado.** `_polar_to_rect_x()` devolve **apenas o x** (`radius * cos(θ)`) e `_rect_to_polar_radius()` devolve **apenas o raio** (`hypot(x,y)`). O `y` e o ângulo são simplesmente perdidos. Uma conversão de coordenadas que entrega uma das duas componentes não é uma conversão — e, sem par, não há leitura por voz possível. O `CalculationResult.value` já é tipado como `float | tuple[float, float]` e o `_format_value()` já tem o ramo de tupla: a infraestrutura foi preparada para o par e nunca ligada. O **ERR-009** do §13 ("Conversão polar ↔ rectangular com dados insuficientes ou inválidos") existe no catálogo e em `ui/shared/error_messages.py`, mas **nunca é levantado** por nenhuma linha do motor.
- **A tecla `?` existe no hardware e não faz nada.** `SW25` (`C0L4`) está na PCB e é lida pelo scanner da matriz, mas `entry_for_keycap("?")` devolve `None` e os dois fronts apenas anunciam "Tecla sem função". É a única tecla livre da matriz — e a mais bem posicionada para resolver um problema real de descoberta: os atalhos do produto (`Ctrl` + `Ans` histórico, `Shift` + `Ans` ler expressão, `Ctrl` + `AC` telas, `Ctrl` + `+`/`-` volume) existem, estão centralizados em `keypad.py`, e **não há nenhuma forma de descobri-los sem ver a tela ou ler a documentação**.

## What Changes

### Fecho automático de parênteses (T05)

- `_normalize()` passa a **fechar os parênteses em falta** no fim da normalização, quando o défice for **inequívoco**: só há abre-parênteses pendentes e nenhum fecha-parênteses órfão. `sqrt(144` → `sqrt(144)` → `12`. O fecho é aplicado após todas as reescritas por regex, para que os parênteses que o próprio motor introduz (fatorial, percentagem, `logbase`) já estejam contabilizados.
- Um fecha-parênteses **sem abertura correspondente** (`2+)`, `sqrt(4))`) continua a ser erro de sintaxe (`ERR-007`): aí não há leitura única e adivinhar seria pior que recusar.
- Uma chamada de função que fique com **argumentos a menos** depois do fecho (`nCr(5` → `ncr(5)`) passa a responder **`ERR-008` "Expressão incompleta" (P2)**, em vez do `TypeError` cru que hoje escapa como `ERR-007`. O código distingue entrada *incompleta* de entrada *inválida*, como o §13 já prevê.

### Combinação e permutação em notação infixa (T06)

- **BREAKING:** o motor passa a aceitar `nCr`/`nPr` **apenas na forma infixa** — `5 nCr 2` → `10`. A forma funcional `nCr(5,2)` deixa de ser válida e responde `ERR-007`.
- `_normalize()` reescreve `A nCr B` → `ncr(A,B)` (idem `nPr`), onde `A` e `B` são operandos atómicos: número, `pi`, `e`, `Ans` já substituído, grupo entre parênteses, ou uma chamada de função. A precedência fica acima de `+`/`-` e abaixo de `^`, consistente com o uso em calculadoras científicas.
- A tecla `nCr` passa a inserir o token infixo `nCr` (primária) e `nPr` (`Ctrl`), em vez de `nCr(` / `nPr(`. A sequência física passa a ser `5` `[nCr]` `2` `[=]`.
- `core/state.py` deixa de listar `"ncr("`, `"npr("`, `"nCr("`, `"nPr("` como tokens de função que abrem parênteses.
- A vírgula (`Shift` + `.`) **permanece**: continua a ser necessária para as conversões de coordenadas, que são genuinamente binárias.

### Conversões de coordenadas completas e leitura padronizada (T08)

- `polar(r, θ)` (polar → retangular) passa a devolver o **par** `(x, y)`; `rect(x, y)` (retangular → polar) passa a devolver o **par** `(r, θ)`, com `θ` calculado por `atan2` e convertido pelo modo angular ativo (DEG/RAD), como o `r` já respeitava.
- O par propaga-se pelo `CalculationResult.value` (tipo já existente) e pelo ramo de tupla do `_format_value()`.
- **Leitura por voz padronizada** (novo `spoken_pair` em `ui/shared/speech_text.py`), com as duas frases fixadas pelo T08:
  - resultado **retangular**: «**x igual a [valor] e y igual a [valor]**»
  - resultado **polar**: «**real [valor], ângulo [valor]**»
  - Cada componente passa pelo `spoken_number()` que já existe, para o separador decimal ser falado como "ponto" e a parte fracionária dígito a dígito.
- Os dois fronts (`ui/lcd/app.py`, `ui/hdmi/app.py`) passam a chamar `spoken_pair` quando `result.value` é tupla, em vez de entregar `"(3, 4)"` ao `spoken_number()` — que hoje devolveria a string intacta e faria o motor neural ler a pontuação.
- **`ERR-009` passa a ser levantado**: conversão com aridade errada ou argumento não numérico (`polar(5)`, `rect(3,4,5)`). O código sai do catálogo morto e passa a ter cobertura.

### Tecla `?` como ajuda falada contextual (T09)

- Novo token de atalho `HELP`, resolvido por `entry_for_keycap("?")`, com nome falado "ajuda".
- Pressionar `?` anuncia o **modo angular ativo** seguido dos atalhos do produto, montados a partir dos rótulos **já centralizados** em `keypad.py` (`HISTORY_SHORTCUT_LABEL`, `SPEAK_EXPRESSION_SHORTCUT_LABEL`, `VOLUME_SHORTCUT_LABEL`, `BLACKOUT_SHORTCUT_LABEL`) — a ajuda não pode divergir dos atalhos reais porque lê a mesma fonte.
- Pressionar `?` **enquanto a ajuda fala** interrompe-a (RF-08: nenhuma fala prolongada bloqueia a entrada). Qualquer outra tecla também a corta, pelo caminho de `interrupt_and_say` que já existe.
- A ajuda **não altera a expressão** nem o estado de cálculo, e funciona igual em modo somente áudio (RF-04/RF-10).
- `NO_FUNCTION_SPEECH` permanece para teclas genuinamente não mapeadas (defeito de hardware, keycap desconhecido), mas deixa de ser o destino da `?`.

### Validação (T11)

- Testes novos em `software/tests/` para cada comportamento acima, incluindo os casos de limite e as entradas inválidas pedidas em T05/T06/T08.
- Os testes existentes que usam a forma funcional de `nCr`/`nPr` são reescritos para a infixa, e os que afirmam que a `?` não tem função são atualizados (ver Impact).

## Não-objetivos

- **Não expandir o catálogo matemático do PRD §5.** Nenhuma operação nova: `nCr`, `nPr`, polar→retangular e retangular→polar já estão no catálogo; esta mudança só as torna alcançáveis e corretas.
- **Não introduzir aritmética complexa geral.** O §5 lista *conversões de coordenadas*, não um tipo numérico complexo. Fica fora: `i` como literal, soma/produto de complexos, módulo e argumento como funções independentes, e exibição em forma `a+bi`.
- **Não criar códigos de erro novos.** Reusa `ERR-007`, `ERR-008` e `ERR-009`, todos já no §13; o `ERR-009` apenas deixa de ser letra morta.
- **Não acoplar o motor a nenhuma UI.** O fecho de parênteses, a notação infixa e os pares de conversão ficam em `core/engine.py`; as frases faladas ficam em `ui/shared/speech_text.py`, sem import de Tkinter/ttkbootstrap.
- **Não mexer na pinagem nem no scanner da matriz.** A `?` já é lida corretamente pelo hardware; só lhe falta destino no software.
- **Não adicionar botão de ajuda na tela.** A `?` não tem posição no teclado da tela (é um espaçador em `LEFT_BUTTONS`) e continua assim: a ajuda é uma função do teclado físico.

## Capabilities

### New Capabilities

- `expression-normalization`: como o motor interpreta o texto que o utilizador construiu antes de o avaliar. Cobre o fecho automático de parênteses inequívocos, a recusa de fechos órfãos, a notação infixa de `nCr`/`nPr`, a distinção entre expressão incompleta (`ERR-008`) e inválida (`ERR-007`), e a garantia de que nada disto depende de uma stack de UI.
- `coordinate-conversion`: as conversões polar ↔ retangular como operações de **par**. Cobre o valor devolvido (duas componentes), o respeito ao modo angular ativo, o `ERR-009` para dados insuficientes ou inválidos, e as duas frases faladas padronizadas para cada sentido da conversão.
- `spoken-help-key`: a tecla `?` da matriz 6x7 como ajuda falada. Cobre o conteúdo anunciado (modo angular + atalhos lidos da fonte única), a interrupção por novo toque, a não interferência na expressão e no estado, e a paridade entre os dois fronts e o modo somente áudio.

### Modified Capabilities

<!-- Nenhuma. As quatro specs existentes (display-switching, hdmi-ui,
     rpi-boot-image, video-output-exclusivity) tratam de seleção de saída de
     vídeo, layout do front HDMI e imagem de boot. Nenhum dos seus requisitos
     muda: a tecla "?" não altera a paridade entre fronts já exigida pela
     hdmi-ui (ela passa a ter função nos DOIS fronts, que é o que aquele
     requisito já pede), e o motor de cálculo não é objeto de nenhuma delas. -->

## Impact

**Código alterado**

- `software/core/engine.py`: fecho de parênteses e reescrita infixa em `_normalize()`; `_polar_to_rect_x`/`_rect_to_polar_radius` substituídas por funções que devolvem par; `ERR-009` e `ERR-008` levantados; aridade das conversões validada.
- `software/core/state.py`: `nCr(`/`nPr(` saem da lista de tokens que abrem parênteses.
- `software/ui/shared/keypad.py`: token da tecla `nCr` passa a infixo; novo token `HELP` + nome falado; `entry_for_keycap("?")` deixa de devolver `None`; texto da ajuda montado dos rótulos de atalho existentes.
- `software/ui/shared/speech_text.py`: novo `spoken_pair` com as duas frases padronizadas.
- `software/ui/lcd/app.py` e `software/ui/hdmi/app.py`: tratamento do token `HELP`; uso de `spoken_pair` para resultados em par. A `?` sai do caminho de `_on_unmapped_key`.

**Testes a atualizar (consequência do BREAKING e da `?`)**

- `software/tests/test_prd_functions.py:49-51` — `nCr(10, 3)` / `nPr(10, 3)` → forma infixa.
- `software/tests/test_core_engine.py:34` — `nCr(5,2)+nPr(4,2)` → forma infixa.
- `software/tests/test_error_messages.py:15` — a expressão que provoca `ERR-004` (`nCr(2, 5)`) → forma infixa.
- `software/tests/test_shift_ans_and_dot_key.py:140,147` — afirma que a tecla produz `nCr(5,2)`; passa a afirmar a sequência infixa.
- `software/tests/test_matrix_input.py:42,59` — afirmam `missing == ["?"]` e `entry_for_keycap("?") is None`; passam a afirmar o token `HELP`.
- `software/tests/test_video_blackout_keys.py:83` — afirma que `?` não é rótulo do teclado da tela; **continua válido** (a `?` segue sem botão) e serve de regressão para o não-objetivo.

**Testes novos**

Fecho de parênteses (simples, aninhado, órfão, múltiplos em falta); infixa de `nCr`/`nPr` (valor esperado `5 nCr 2 = 10`, limites `n = r`, `r = 0`, inválidos `n < r`, negativos, não inteiros → `ERR-004`); conversões em par nos dois sentidos em DEG e RAD, `ERR-009`, e as duas frases de `spoken_pair`; tecla `?` (conteúdo da ajuda, interrupção, expressão intacta, paridade entre fronts).

**Documentação**

- `docs/comandos-teclado.md`: a `?` passa a ter função; a sequência de `nCr`/`nPr` muda.
- `docs/produto/PRD.md` §13: registar que `ERR-009` passou a ser emitido e que `ERR-008` cobre aridade incompleta (o §13 exige registo de códigos ao serem implementados; nenhum código novo é criado).

**Sem impacto**

Dependências (nenhuma nova; `math.comb`, `math.perm`, `math.atan2` são da biblioteca padrão), pinagem e scanner da matriz, seleção de saída de vídeo, UPS, volume, e o pipeline de CI (continua `python -m unittest`).
