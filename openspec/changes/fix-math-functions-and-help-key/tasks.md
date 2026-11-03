## 1. Motor: fecho automático de parênteses (T05)

- [x] 1.1 Em `software/core/engine.py`, acrescentar um varrimento de profundidade que, no **fim** de `_normalize()`, conte `(` e `)`; se a profundidade ficar negativa em qualquer ponto, devolver o texto inalterado (fecho órfão → `ast.parse` produz `ERR-007`); se terminar positiva, acrescentar os `)` em falta. Comentar porque corre no fim (fatorial, percentagem e `logbase` injetam parênteses).
- [x] 1.2 Garantir que `CalculationResult.expression` continua a ser o texto **original** do utilizador, não o texto com os fechos acrescentados.
- [x] 1.3 Novo teste `software/tests/test_paren_autoclose.py`: `sqrt(144` → `12`; `(2+3` → `5`; `sqrt((4` → `2`; `sqrt(16)+(2*3` → `10`; `(50%` → `0.5`; e `sqrt(144)` inalterado (regressão).
- [x] 1.4 No mesmo ficheiro, testes de recusa: `2+)`, `sqrt(4))` e `)2+(3` → todos `ERR-007` com prioridade `P1`; confirmar que o último **não** é fechado apesar de ter um `(` pendente.
- [x] 1.5 Teste de que a expressão original é preservada: `evaluate("sqrt(144").expression == "sqrt(144"`.

## 2. Motor: aridade e códigos de erro (T05/T08)

- [x] 2.1 Em `_eval_call()`, consultar uma tabela `nome → aridade esperada` e validar **antes** de invocar a função, substituindo o `TypeError` cru que hoje escapa como `ERR-007` com mensagem em inglês.
- [x] 2.2 Aplicar a regra única da `design.md` §4: argumentos a menos → `ERR-008` (P2) para qualquer função; argumentos a mais → `ERR-009` (P1) nas conversões, `ERR-007` (P1) nas restantes.
- [x] 2.3 Testes em `software/tests/test_core_engine.py`: `polar(5` e `logbase(2` → `ERR-008`/P2; `polar(5, 30, 2)` e `rect(3, 4, 5)` → `ERR-009`/P1; `evaluate("")` continua `ERR-008`/P2.
- [x] 2.4 Em `software/tests/test_error_messages.py`, acrescentar `ERR-009` ao mapeamento código → expressão que o provoca, confirmando que a mensagem vem de `ERROR_MESSAGES["ERR-009"]` e que o prefixo falado é "Erro" (P1).

## 3. Motor: notação infixa de nCr/nPr (T06) — **BREAKING**

- [x] 3.1 Implementar em `engine.py` a procura de operandos por varrimento de delimitadores (`design.md` §3): para cada `nCr`/`nPr` (insensível a caixa), caminhar para a esquerda e para a direita consumindo um átomo — número, `pi`, `e`, grupo `(...)` equilibrado, ou chamada de função (identificador imediatamente antes do `(`) — e reescrever `A nCr B` → `ncr(A,B)`, repetindo até não haver ocorrências.
- [x] 3.2 Colocar esta reescrita **depois** do fecho automático da tarefa 1.1, e registar a dependência de ordem em comentário: com os parênteses já equilibrados, o varrimento de átomos nunca encontra um grupo sem fecho.
- [x] 3.3 Levantar `ERR-008` (P2) quando faltar o átomo de um dos lados (`5 nCr`, `nCr 2`).
- [x] 3.4 Remover `ncr`/`npr` da tabela de funções chamáveis, de modo que `nCr(5,2)` passe a devolver `ERR-007`; manter `_ncr`/`_npr` e `_validate_combinatorics` como destino da reescrita interna.
- [x] 3.5 Em `software/core/state.py`, remover `"ncr("`, `"npr("`, `"nCr("` e `"nPr("` da lista de tokens que abrem parênteses.
- [x] 3.6 Em `software/ui/shared/keypad.py`, trocar a entrada da tecla `nCr` de `("nCr", "nCr(", "nPr(", None)` para os tokens infixos `("nCr", "nCr", "nPr", None)`, e atualizar `SPOKEN_TOKEN_NAMES` (`"nCr"` → "combinação", `"nPr"` → "permutação") sem perder os nomes falados.
- [x] 3.7 Ajustar `button_style()` em `keypad.py`, que hoje categoriza por `"nCr("` e por conter `"nPr"`, para os novos tokens.
- [x] 3.8 Verificar que a vírgula (`Shift` + `.`) continua a produzir `,`: as conversões de coordenadas ainda precisam dela.
- [x] 3.9 Novo teste `software/tests/test_combinatorics_infix.py`: `5 nCr 2` → `10`; `5nCr2` → `10`; `5 nPr 2` → `20`; `5 NCR 2` → `10`; `2 + 5 nCr 2` → `12`; `(4+1) nCr (1+1)` → `10`; `sqrt(25) nCr 2` → `10`; `Ans nCr 2` com `ans=5` → `10`.
- [x] 3.10 No mesmo ficheiro, limites e inválidos: `5 nCr 5` → `1`; `5 nCr 0` → `1`; `2 nCr 5`, `5 nCr -2` e `5.5 nCr 2` → `ERR-004`; `5 nCr` → `ERR-008`/P2; `nCr(5,2)` → `ERR-007` (fixa o BREAKING).
- [x] 3.11 Testes da interação com a tarefa 1: `sqrt(9 nCr 2` → `6` (o fecho cai no fim, logo a combinação fica *dentro* da raiz: `sqrt(C(9,2))` = `sqrt(36)`) e `5 nCr (2` → `10`, exercitando a ordem fecho-antes-de-infixa nos dois sentidos.
- [x] 3.12 Fixar por teste o caso aberto da `design.md`: `Ans nCr 2` com `ans=-5` resolve para `-ncr(5,2)` (o menos unário fica fora do átomo), consistente com o resto do motor.

## 4. Motor: conversões de coordenadas como par (T08)

- [x] 4.1 Substituir `_polar_to_rect_x` por uma função que devolve o par `(r·cos θ, r·sin θ)`, mantendo a conversão do ângulo pelo modo angular ativo.
- [x] 4.2 Substituir `_rect_to_polar_radius` por uma função que devolve o par `(hypot(x,y), atan2(y,x))`, com o ângulo convertido para a unidade do modo ativo — `atan2` e não `atan(y/x)`, pelo quadrante correto e por não dividir por zero quando `x = 0`.
- [x] 4.3 Alargar a anotação de tipo de `_functions()` para `Callable[..., float | tuple[float, float]]`.
- [x] 4.4 Em `_eval_binary`, `_eval_unary` e `_eval_call`, verificar explicitamente se um operando é tupla e levantar `ERR-007`: um par só é válido como expressão completa, e sem esta verificação `polar(2,60)+1` sairia como `TypeError`.
- [x] 4.5 Acrescentar a `software/core/models.py` o campo que transporta o **sentido** da conversão em `CalculationResult` (retangular ou polar; `None` para resultados escalares), com valor por omissão para não quebrar as construções existentes.
- [x] 4.6 Em `evaluate()`, determinar o sentido **uma vez** a partir de `tree.body`: `Call` a `polar` → par retangular; a `rect` → par polar; caso contrário `None`.
- [x] 4.7 Testes em `software/tests/test_coordinate_conversion.py` para polar → retangular: `polar(2, 60)` em `deg` → `(1.0, 1.7320508075688772)`; `polar(1, 0)` em `deg` e em `rad` → `(1.0, 0.0)`; `polar(0, 45)` → `(0.0, 0.0)`.
- [x] 4.8 No mesmo ficheiro, retangular → polar: `rect(3, 4)` em `deg` → `(5.0, 53.13010235415598)`; `rect(0, 1)` em `deg` → `(1.0, 90.0)` sem divisão por zero; `rect(-1, 0)` em `deg` → `(1.0, 180.0)` (quadrante); `rect(1, 1)` em `rad` → `(1.4142135623730951, 0.7853981633974483)`; `rect(0, 0)` → `(0.0, 0.0)`.
- [x] 4.9 No mesmo ficheiro, par só no topo: `polar(2, 60) + 1`, `sqrt(rect(3, 4))` e `rect(3, 4) nCr 2` → `ERR-007`; `rect(3, 4)` sozinho → sucesso com par.
- [x] 4.10 No mesmo ficheiro, sentido da conversão: `polar(2,60)` identificado como retangular, `rect(3,4)` como polar, e `2+2` sem sentido associado.

## 5. Voz: leitura padronizada dos pares (T08)

- [x] 5.1 Em `software/ui/shared/speech_text.py`, acrescentar `spoken_pair(pair, kind)` que compõe cada componente com o `spoken_number()` existente e devolve «x igual a [valor] e y igual a [valor]» para `kind` retangular e «real [valor], ângulo [valor]» para `kind` polar.
- [x] 5.2 Testes em `software/tests/test_speech_text.py`: `(1.0, 1.7320508075688772)` retangular → `"x igual a 1 e y igual a 1 ponto 7 3 2 0 5 0 8 0 8"`; `(1.0, 0.0)` → `"x igual a 1 e y igual a 0"`; `(-1.0, 0.0)` → `"x igual a menos 1 e y igual a 0"`.
- [x] 5.3 No mesmo ficheiro, lado polar: `(5.0, 53.13010235415598)` → `"real 5, ângulo 53 ponto 1 3 0 1 0 2 3 5"`; `(1.0, 90.0)` → `"real 1, ângulo 90"`.
- [x] 5.4 Teste de regressão de que `spoken_number` continua a tratar escalares como hoje, e de que nenhum texto produzido por `spoken_pair` contém `(`, `)` ou `,` como caractere a ser lido literalmente.

## 6. Voz: ajuda da tecla ? (T09)

- [x] 6.1 Em `software/ui/shared/keypad.py`, acrescentar o token de atalho `HELP` e o seu nome falado ("ajuda") a `SPOKEN_TOKEN_NAMES`.
- [x] 6.2 Declarar `HELP_ENTRIES` como fonte única: por atalho, a descrição e as combinações em **tokens** `(modificador, tecla)` — histórico, ler expressão atual, volume (duas combinações) e apagar/religar telas — reaproveitando os tokens já declarados (`HISTORY_TOKEN`, `SPEAK_EXPRESSION_TOKEN`, `VOLUME_UP_TOKEN`, `VOLUME_DOWN_TOKEN`, `BLACKOUT_TOKEN`).
- [x] 6.3 Implementar `help_speech(angle_mode)` como função pura: identifica a ajuda, anuncia o modo angular ativo, e rende uma linha por entrada com as teclas faladas por `spoken_token` ("controle mais resposta anterior"), nunca pelos rótulos visuais.
- [x] 6.4 Fazer `entry_for_keycap("?")` devolver o token `HELP` em vez de `None`, mantendo o retorno `None` (e o `NO_FUNCTION_SPEECH`) para keycaps genuinamente fora do mapa.
- [x] 6.5 Confirmar que a `?` continua **sem botão na tela**: a posição em `LEFT_BUTTONS` fica espaçador e o comentário é atualizado (a tecla já tem função, só não tem botão).
- [x] 6.6 Em `software/hw_platform/keyboard.py`, mapear `"?"` → `HELP` em `KEY_MAP`, para a ajuda ser exercitável no PC como o `"a"` → `"Ans"` já faz para o histórico.
- [x] 6.7 Novo teste `software/tests/test_help_key.py`: conteúdo de `help_speech("deg")` e `help_speech("rad")` anuncia o modo correto; o texto não contém `+` nem `/` como representação de teclas.
- [x] 6.8 No mesmo ficheiro, o teste **anti-deriva**: enumerar os tokens de atalho declarados em `keypad.py` e falhar se algum não estiver coberto por `HELP_ENTRIES`.
- [x] 6.9 No mesmo ficheiro, `entry_for_keycap("?")` devolve `HELP`, e `?` não consta dos rótulos do teclado da tela.

## 7. Fronts: despacho e paridade (T08/T09)

- [x] 7.1 Em `software/ui/lcd/app.py`, tratar o token `HELP` no `_handle_token()` ao lado de `HISTORY` e `BLACKOUT`: anunciar `help_speech(self.state.angle_mode)` por `interrupt_and_say` e retornar sem tocar no `CalculatorState`.
- [x] 7.2 Em `ui/lcd/app.py`, usar `spoken_pair` quando `result.value` for tupla, escolhendo a frase pelo sentido transportado no resultado, em vez de passar o `display` da tupla a `spoken_number`.
- [x] 7.3 Replicar 7.1 e 7.2 em `software/ui/hdmi/app.py`, mantendo o texto anunciado idêntico ao do LCD.
- [x] 7.4 Verificar que a `?` deixa de passar por `_on_unmapped_key` nos dois fronts, e que teclas desconhecidas continuam a anunciar `NO_FUNCTION_SPEECH`.
- [x] 7.5 Atualizar `software/tests/test_matrix_keys_in_fronts.py` (hoje pressiona `"?"` esperando tecla sem função) para o novo comportamento.
- [x] 7.6 Testes de que `HELP` não altera estado: expressão `5 nCr 2` intacta após `?`; resultado e `Ans` intactos; modo angular intacto apesar de ser anunciado.
- [x] 7.7 Teste de interrupção: `?` seguido de `?` não reproduz a ajuda em simultâneo; `?` seguido de `7` corta a fala, insere o dígito e anuncia-o.

## 8. Atualizar testes existentes afetados pelo BREAKING

- [x] 8.1 `software/tests/test_prd_functions.py:49-51` — `nCr(10, 3)` → `10 nCr 3` e `nPr(10, 3)` → `10 nPr 3`, preservando os valores esperados `120` e `720`.
- [x] 8.2 `software/tests/test_core_engine.py:34` — `nCr(5,2)+nPr(4,2)` → forma infixa, preservando o valor esperado.
- [x] 8.3 `software/tests/test_error_messages.py:15` — a expressão que provoca `ERR-004` (`nCr(2, 5)`) → `2 nCr 5`.
- [x] 8.4 `software/tests/test_shift_ans_and_dot_key.py:140,147` — a asserção de que a tecla produz `nCr(5,2)` passa a afirmar a sequência infixa `5 nCr 2`.
- [x] 8.5 `software/tests/test_matrix_input.py:42,59` — `missing == ["?"]` e `entry_for_keycap("?") is None` passam a refletir o token `HELP`.
- [x] 8.6 Confirmar que `software/tests/test_video_blackout_keys.py:83` (a `?` não é rótulo do teclado da tela) **continua a passar sem alteração**, servindo de regressão ao não-objetivo "sem botão de ajuda".

## 9. Documentação

- [x] 9.1 `docs/comandos-teclado.md`: a tecla `?` passa a ter função (ajuda falada, interrompível); a sequência de `nCr`/`nPr` passa a infixa; remover a afirmação de que a `?` não tem função no catálogo.
- [x] 9.2 `docs/produto/PRD.md` §13: registar que `ERR-009` passou a ser emitido pelo motor e que `ERR-008` cobre aridade incompleta — o §13 exige registo dos códigos ao serem implementados; **nenhum código novo é criado** e o catálogo da §5 não muda.
- [x] 9.3 Acrescentar ao §14 (histórico de versões do PRD) a linha correspondente a esta mudança.

## 10. Validação final (T11)

- [x] 10.1 Correr a suite completa num ambiente com as dependências gráficas instaladas (`python -m pip install -r software/requirements.txt`) e confirmar que passa inteira. Num ambiente **sem** essas dependências, confirmar que a **causa** dos abortos continua a ser só a ausência de `ttkbootstrap` — a contagem sobe com os testes de front novos, o que não é regressão; o invariante é não aparecer nenhuma causa nova.
- [x] 10.2 Validar os resultados matemáticos pedidos nas tarefas do TCC: `5 nCr 2` → `10`; `sqrt(144` → `12`; `polar(...)` e `rect(...)` devolvem os dois valores nos dois modos angulares.
- [x] 10.3 Verificar a coerência do feedback sonoro ponta a ponta: as duas frases padronizadas dos pares, o anúncio da ajuda, e as mensagens de `ERR-007`/`ERR-008`/`ERR-009` com o prefixo de prioridade correto ("Erro" para P1, "Aviso" para P2), conforme o RF-07.
- [x] 10.4 Confirmar que nenhuma funcionalidade existente regrediu: histórico, `Ans`, `RAD/DEG`, volume, blackout de telas e alerta de bateria continuam a passar nos seus testes.
- [x] 10.5 Confirmar que `software/core/` continua sem importar nenhuma stack de UI (§8) e que `python -c "import software.core.engine"` funciona num ambiente sem dependências gráficas.
- [x] 10.6 Correr `openspec validate fix-math-functions-and-help-key --strict` e resolver o que apontar.
