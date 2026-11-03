## Context

O motor (`software/core/engine.py`) avalia expressões em dois passos: `_normalize()` reescreve o texto do utilizador por **regex sucessivas** até ele ser Python válido, e depois `ast.parse(mode="eval")` + um visitador de nós (`_eval_node`) avalia uma árvore restrita — sem `eval()`, só `Constant`, `Name`, `UnaryOp`, `BinOp` e `Call` com nomes de uma tabela fixa. Esta mudança atua **inteiramente nessa fronteira**: três dos quatro defeitos são falhas de normalização ou da tabela de funções, e nenhum exige um parser novo.

Estado relevante para as decisões:

- `_normalize()` é uma sequência linear de ~25 reescritas. Algumas **introduzem parênteses** (`_replace_factorials`, `_replace_percentages`, `log2(` → `logbase(2, `), o que torna a ordem relativa ao fecho automático uma decisão real, não um detalhe.
- `_eval_node()` tem assinatura `-> float`. O `CalculationResult.value` já é `float | tuple[float, float]` e `_format_value()` já trata tupla: o par foi previsto no modelo e nunca ligado. Logo, os pares são um problema de **propagação**, não de modelagem.
- `_eval_call()` faz `function(*args)` sem validar aridade. Qualquer erro de aridade sai como `TypeError`, que o `except` genérico do `evaluate()` converte em `ERR-007` com a mensagem crua do Python ("takes 2 positional arguments but 1 was given") — texto em inglês que o TTS leria em voz alta.
- Os dois fronts (`ui/lcd/app.py`, `ui/hdmi/app.py`) despacham tokens de ação (`HISTORY`, `BLACKOUT`, `VOL_UP/DOWN`, `SPEAK_EXPR`, `RAD/DEG`) num `_handle_token()` com a mesma forma. O vocabulário falado e os rótulos de atalho estão **centralizados** em `ui/shared/keypad.py`, e é essa centralização que torna a ajuda da tecla `?` barata.

Restrições que moldam o desenho: o catálogo matemático do PRD §5 é fechado; os códigos de erro do §13 não se inventam; o `core/` não pode importar UI (§8); e o produto tem de funcionar **sem tela** (RF-04/RF-10), o que faz do texto falado parte do contrato, não um extra.

## Goals / Non-Goals

**Goals:**

- Tornar `sqrt(144`, `5 nCr 2`, `polar(...)` e `rect(...)` operacionais pela sequência natural do teclado físico 6x7.
- Fazer os pares de coordenadas atravessarem motor → resultado → voz com uma frase padronizada por sentido.
- Dar função à única tecla livre da matriz (`?`) resolvendo o problema de **descoberta** dos atalhos sem tela.
- Substituir mensagens de erro cruas do Python por códigos do §13 com a prioridade certa (P1 vs P2).
- Manter toda a lógica nova testável sem GUI: hoje 92 dos 449 testes já não correm num ambiente sem `ttkbootstrap`, e nada do que acrescentamos deve aumentar esse número.

**Non-Goals:**

- Substituir a normalização por regex por um tokenizador/parser próprio. É tentador (ver Riscos), mas é uma reescrita do motor e sai do âmbito destas cinco tarefas.
- Aritmética de números complexos (soma, produto, `i`, forma `a+bi`). O §5 lista *conversões de coordenadas*, e o T08 pede padronizar a **leitura** delas — não um tipo numérico novo.
- Fecho automático de operadores pendentes (`2+` → `2`). Só parênteses; um operador pendente continua `ERR-008`.
- Botão de ajuda na tela, ou ajuda por menus navegáveis. A ajuda é uma fala única, interrompível.

## Decisions

### 1. O fecho de parênteses é um varrimento de profundidade no **fim** da normalização

Um contador de profundidade percorre o texto já normalizado: `(` incrementa, `)` decrementa. Se a profundidade ficar **negativa** em qualquer ponto, existe um fecho órfão e **nada** é acrescentado — o texto segue como está e o `ast.parse()` produz o `ERR-007` que já produz hoje. Se terminar positiva, acrescentam-se tantos `)` quantos a profundidade final.

Correr **no fim** é o que torna o resultado correto: as reescritas de fatorial, percentagem e `logbase` injetam parênteses equilibrados, e contá-los antes daria um défice errado. Expressões de calculadora não têm literais de texto nem comentários, portanto um varrimento de caracteres é exato — não há caso em que um `(` seja "falso".

*Alternativa considerada:* contar parênteses no texto **original** do utilizador e acrescentar os fechos antes das reescritas. Rejeitada porque obriga cada reescrita futura a manter o equilíbrio por sua conta, transformando uma invariante local numa global frágil.

*Alternativa considerada:* tentar `ast.parse()` e, ao receber `SyntaxError` com a mensagem `'(' was never closed`, acrescentar um `)` e repetir. Rejeitada por depender do **texto** de uma mensagem de erro do CPython, que muda entre versões (a frase atual é de 3.10+).

### 2. O fecho corre **antes** da reescrita infixa de `nCr`/`nPr`

Esta ordem é o que torna a decisão 3 possível. Com os parênteses já equilibrados, a procura dos operandos de um operador infixo é um varrimento de delimitadores **bem definido**: nunca encontra um grupo sem fecho.

Verificado nos dois sentidos que importam:

- `sqrt(25 nCr 2` → fecho dá `sqrt(25 nCr 2)` → infixa dá `sqrt(ncr(25,2))` ✔
- `5 nCr (2` → fecho dá `5 nCr (2)` → infixa dá `ncr(5,(2))` ✔

A ordem inversa falharia no segundo caso, porque o operando direito começaria num grupo sem fecho.

### 3. Os operandos infixos são encontrados por varrimento de delimitadores, não por regex

Para cada ocorrência de `nCr`/`nPr` (insensível a caixa), o algoritmo caminha:

- **para a esquerda**, saltando espaços, e consome um átomo: se encontrar `)`, caminha até ao `(` que o equilibra e, se imediatamente antes houver um identificador, inclui-o (é uma chamada de função); senão, consome o literal numérico ou a constante;
- **para a direita**, simetricamente.

Depois substitui `A nCr B` por `ncr(A,B)` e repete até não haver mais ocorrências (a avaliação da esquerda para a direita dá associatividade à esquerda).

Isto é ~30 linhas e trata corretamente `sqrt(25) nCr (1+1)`, que uma regex não trata: parênteses aninhados não são uma linguagem regular. A precedência acima de `+`/`-` sai de graça — o átomo da esquerda é `2` em `2 + 5 nCr 2`, logo a reescrita é `2+ncr(5,2)`.

Se um dos lados não tiver átomo (`5 nCr`, `nCr 2`), levanta-se `ERR-008` **P2** diretamente: é entrada incompleta, exatamente o que o §13 reserva para esse código.

*Alternativa considerada:* uma regex com um padrão de átomo que cobre um nível de parênteses. Rejeitada por falhar em silêncio no segundo nível — e falhar em silêncio num motor de cálculo é o pior modo de falha possível.

*Alternativa considerada:* manter também a forma funcional `nCr(5,2)` e aceitar as duas. Rejeitada por decisão de produto (ver proposta): uma forma só mantém a especificação e os testes sem ambiguidade. O custo é assumido e explícito — **BREAKING**, com os testes existentes reescritos nesta mudança.

### 4. A aridade é validada por tabela, antes da chamada

`_eval_call()` passa a consultar uma tabela `nome → aridade esperada` e aplicar uma regra única:

| Situação | Código | Prioridade | Porquê |
|---|---|---|---|
| argumentos **a menos** (qualquer função) | `ERR-008` | P2 | entrada incompleta; é o que acontece quando o fecho automático fecha cedo (`polar(5`) |
| argumentos **a mais** numa conversão | `ERR-009` | P1 | o §13 reserva o 009 a "dados insuficientes ou inválidos para a conversão" |
| argumentos **a mais** noutra função | `ERR-007` | P1 | expressão sintaticamente inválida |

Validar **antes** de chamar evita que um `TypeError` em inglês chegue ao TTS, e é o que finalmente dá uso ao `ERR-009` — hoje presente no §13 e em `error_messages.py` mas nunca emitido por nenhuma linha do motor.

### 5. O sentido da conversão é lido do nó de topo, não transportado pela avaliação

As duas funções de conversão passam a devolver `tuple[float, float]`. Um par **não tem aritmética definida** no §5, logo só é válido como expressão inteira: `_eval_binary`, `_eval_unary` e `_eval_call` verificam explicitamente se um operando é tupla e levantam `ERR-007` se for. Sem essa verificação, `polar(2,60)+1` sairia como um `TypeError` cru.

Como consequência dessa restrição, `evaluate()` sabe o sentido da conversão olhando **uma vez** para `tree.body`: se for um `Call` a `polar`, o par é retangular; se for a `rect`, é polar. Esse sentido vai num campo novo de `CalculationResult`, e os fronts escolhem a frase sem reinterpretar a expressão.

*Alternativa considerada:* um tipo embrulhado (`CoordinatePair`) devolvido pelas funções e propagado pela avaliação. Rejeitada por obrigar `_eval_node` a lidar com dois tipos de retorno em todos os caminhos, quando a restrição "só no topo" já resolve o problema com uma verificação local.

*Alternativa considerada:* o front detetar `"polar("` / `"rect("` na string da expressão. Rejeitada: é reinterpretação frágil da entrada (`"polar"` pode aparecer num `Ans` substituído) e põe conhecimento do motor no front, contra o §8.

### 6. As frases faladas são uma função pura em `ui/shared/speech_text.py`

`spoken_pair(pair, kind)` devolve `"x igual a … e y igual a …"` para `kind="rect"` e `"real …, ângulo …"` para `kind="polar"`, compondo cada componente com o `spoken_number()` existente — que já resolve o problema real do separador decimal (o Piper lê "1.2" como "um dois") e lê a parte fracionária dígito a dígito.

Fica em `speech_text.py` e não nos fronts porque os dois fronts e o modo somente áudio têm de dizer **a mesma coisa** (RF-04/RF-10), e porque uma função pura de tupla para string é testável sem Tk — ao contrário dos fronts, cujos testes já não correm sem `ttkbootstrap`.

### 7. A ajuda da tecla `?` deriva de uma estrutura única, que os testes obrigam a cobrir

Acrescenta-se a `keypad.py` uma estrutura `HELP_ENTRIES`: para cada atalho, a sua descrição e as combinações `(modificador, tecla)` em **tokens**. A função `help_speech(angle_mode)` monta o anúncio: identificação, modo angular, e uma linha por entrada, com as teclas faladas por `spoken_token` ("controle mais resposta anterior"), nunca pelos rótulos visuais ("Ctrl + Ans") — um `+` lido literalmente soaria "mais" no meio de uma frase sobre teclas.

O ponto importante é a **anti-deriva**: um teste enumera os tokens de atalho declarados (`HISTORY_TOKEN`, `SPEAK_EXPRESSION_TOKEN`, `VOLUME_UP_TOKEN`, `VOLUME_DOWN_TOKEN`, `BLACKOUT_TOKEN`) e falha se algum não aparecer em `HELP_ENTRIES`. Assim, acrescentar um atalho no futuro e esquecer a ajuda passa a ser um teste vermelho, não uma lacuna silenciosa — que é exactamente o modo como os atalhos atuais ficaram indescobríveis.

`help_speech` é pura e vive em `ui/shared/`, pelo mesmo motivo da decisão 6.

### 8. `HELP` é um token de ação, igual aos atalhos que já existem

Entra no `_handle_token()` dos dois fronts ao lado de `HISTORY` e `BLACKOUT`, retorna sem tocar no `CalculatorState`, e usa o `interrupt_and_say` já existente — o que dá de graça as duas propriedades pedidas: um segundo toque na `?` corta a fala anterior, e qualquer outra tecla também (RF-08).

`entry_for_keycap("?")` passa a devolver o token em vez de `None`, e `KeyboardAdapter.KEY_MAP` ganha `"?" → "HELP"` para a ajuda ser exercitável no PC, como o `"a" → "Ans"` já faz para o histórico.

## Risks / Trade-offs

- **A reescrita infixa é mais um passo numa cadeia de regex já longa e sensível à ordem.** `_normalize()` tem ~25 reescritas e esta mudança acrescenta duas, uma delas com dependência de ordem explícita (decisão 2) → Mitigação: as duas novas correm **no fim**, depois de toda a canonicalização de nomes; a dependência de ordem fica comentada no código e coberta por testes que a exercitam nos dois sentidos (`sqrt(25 nCr 2`, `5 nCr (2`). A dívida de fundo — trocar regex por um tokenizador — fica registada como não-objetivo, não resolvida.

- **BREAKING: `nCr(5,2)` deixa de calcular.** Qualquer expressão guardada no histórico da sessão, ou escrita em documentação e nos exemplos do TCC, passa a dar `ERR-007` → Mitigação: o histórico não é persistido entre sessões (decisão registada no PRD §6/RNF-05, "sem persistência obrigatória"), portanto o impacto é só na sessão corrente e na documentação, que esta mudança atualiza. Os quatro testes que usam a forma funcional são reescritos aqui, não removidos.

- **O fecho automático pode calcular algo que o utilizador não quis.** `sqrt(16)+(2*3` dá 10 em vez de avisar que falta um fecho → Mitigação: é o comportamento deliberado e é o de uma calculadora científica física; a expressão **original** continua em `CalculationResult.expression` e visível na linha de cálculo, e `Shift` + `Ans` lê-a de volta, pelo que o utilizador consegue verificar o que escreveu. O caso ambíguo (fecho órfão) continua a ser recusado.

- **Os testes dos fronts não correm neste ambiente.** 92 dos 449 testes abortam por falta de `ttkbootstrap`, e os comportamentos de `HELP` e da fala de pares vivem parcialmente nos fronts → Mitigação: a lógica fica nas funções puras (`help_speech`, `spoken_pair`), onde é testada sem GUI; nos fronts fica apenas o despacho. A validação do T11 corre no CI (`.github/workflows/ci.yml`, Python 3.11 com as dependências instaladas), onde a suite completa é significativa.

- **A ajuda pode ficar longa e irritante.** Cinco atalhos ditos em sequência levam vários segundos → Mitigação: é interrompível por qualquer tecla (RF-08) e o utilizador aprende a cortá-la; o modelo de frase do §13 ("evitar mensagens excessivamente longas") é respeitado por linha, e a ordem põe primeiro o que muda (modo angular) e depois os atalhos.

- **`ERR-008` passa a aparecer em casos onde hoje aparece `ERR-007`.** É uma mudança de código de erro observável, e P2 em vez de P1 → Mitigação: é a correção pretendida, não um efeito colateral — o §13 define o 008 como "entrada incompleta ao pedir avaliação", que descreve exatamente `polar(5` e `5 nCr`. Os testes de `test_error_messages.py` fixam a correspondência.

## Migration Plan

1. **Motor primeiro, com testes** (fecho de parênteses, aridade, infixa, pares): `core/engine.py` e `core/models.py` são independentes da UI e a sua suite corre em qualquer ambiente. Ao fim deste passo, `5 nCr 2 = 10` e `sqrt(144) = 12` verificam-se por teste.
2. **Reescrever os testes existentes** que usam a forma funcional (quatro ficheiros, listados na proposta). Este passo é o que torna o BREAKING explícito no diff e revisável no PR.
3. **Camada de voz** (`speech_text.spoken_pair`, `keypad.HELP_ENTRIES` + `help_speech`): funções puras, testadas sem GUI.
4. **Fronts e teclado** (`ui/lcd/app.py`, `ui/hdmi/app.py`, `keypad.py`, `keyboard.py`, `state.py`): despacho de `HELP`, uso de `spoken_pair`, token infixo na tecla `nCr`.
5. **Documentação** (`docs/comandos-teclado.md`, PRD §13) e **validação final** (T11), com a suite completa num ambiente com as dependências gráficas.

**Rollback:** a mudança é um conjunto de commits num branch de funcionalidade, sem migração de dados nem estado persistido (o histórico vive na sessão). Reverter o merge restaura o comportamento anterior sem passos adicionais. Os passos 1 e 3 são independentes do 4 e podem ser revertidos isoladamente se um front regredir.

## Open Questions

- **O `display` de um par.** `_format_value()` já formata tupla como `"(3, 4)"`. Fica assim, ou passa a algo mais legível na tela (`"x=3  y=4"` / `"r=5  θ=53,13"`)? A **fala** está fixada pelo T08; o texto **visual** não, e o PRD não o especifica. Proposta: manter `"(3, 4)"` nesta mudança (menor diff, nenhum teste de layout afetado) e tratar a apresentação visual como ajuste de UI separado, se a banca o pedir.
- **Separador decimal visual.** Os resultados aparecem com ponto (`53.13010235`) embora a voz diga "ponto" e o produto seja pt-BR. É pré-existente e fora do âmbito, mas torna-se mais visível com dois números por resultado.
- **`nCr` com `Ans` à esquerda sem parênteses.** `Ans nCr 2` funciona porque o `Ans` é substituído pelo seu valor **antes** da reescrita infixa. Se o valor for negativo (`-5`), o átomo da esquerda passa a ser `5` e o sinal fica de fora, dando `-ncr(5,2)` em vez de `ERR-004`. Vale fixar por teste qual dos dois é o comportamento desejado? Proposta: `-ncr(5,2)`, por ser consistente com a precedência do menos unário no resto do motor.
