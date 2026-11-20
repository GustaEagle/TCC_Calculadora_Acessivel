## Why

O teste do aparelho deixou pendentes cinco tarefas do cronograma do TCC (T01, T02, T03, T04 e T07) e a parte final da T08. Quatro delas são sobre a **voz**, que é o canal principal do produto para quem não vê a tela (RF-04, RF-10). A quinta é sobre resultados matemáticos que divergem de uma calculadora comercial.

Diagnóstico no código atual:

- **T01 e T04 provavelmente têm a mesma causa.** Cada frase espera a síntese **inteira** terminar e só então abre um processo **novo** de `aplay` (`_RawPlaybackProcess` em `accessibility/speech.py`). O dispositivo de áudio arranca a frio a cada frase, e saídas HDMI costumam descartar o início de um fluxo. Isso explica as duas queixas:
  - O "**impa** tudo" no lugar de "limpar tudo" perdeu justamente o primeiro fonema. O texto enviado ao motor está correto.
  - A espera depois do `=` soma a síntese da frase completa (que, com o decimal lido dígito a dígito, é longa), o arranque do `aplay` e a abertura do dispositivo, antes de soar qualquer coisa.
  Ainda é hipótese: só se confirma no Pi. Por isso a change mede antes de corrigir.
- **T02:** o decimal é lido "1 **ponto** 2". O pedido é "um **vírgula** dois", que é a convenção pt-BR. A escolha de "ponto" foi deliberada numa change anterior, e por isso mudá-la altera specs já arquivadas (`coordinate-conversion`).
- **T03:** "sqrt(9)" é lido "raiz quadrada 9 **fecha parênteses**": o fecho é anunciado e a abertura não. Quem ouve não sabe onde a função começou.
- **T07:** precedência e associatividade estão certas (`2^3^2` = 512, `-2^2` = −4, `2-3-4` = −5). Faltam três coisas:
  - **Multiplicação implícita** não existe: `2(3)`, `2sqrt(9)`, `2π` e `3Ans` dão `ERR-007`. Uma calculadora comercial dá 6, 6, 6,28 e 3×Ans.
  - **`2e3` dá 2000 sem aviso**, porque o Python lê como notação científica. Quem pressiona `2`, `e`, `3` quer 2×*e*×3 = 16,31. É um resultado **errado e silencioso**, o pior modo de falha numa calculadora.
  - **Porcentagem** e a **prioridade** da multiplicação implícita mudam conforme o modelo de calculadora usado como referência. A equipe ainda vai definir o modelo, e essas duas ficam como questão aberta.
- **Bug do modo somente áudio:** `audio_only.py` fala `spoken_number(result.display)` em vez da leitura de pares. Ali `Pol(3,4)` é lido com a pontuação da tupla, o que viola a paridade de fronts exigida pela spec `coordinate-conversion` (RF-10).

## What Changes

### Pronúncia e corte do início da fala (T01)

- **Medir primeiro.** Gravar no Pi as palavras curtas reclamadas (`AC`, `3`, `4`, `π`, parênteses) e confirmar se o problema é o corte do início do áudio ou a pronúncia em si.
- **Silêncio inicial em toda frase:** um intervalo curto de PCM em silêncio antes do áudio, para o dispositivo de saída acordar antes do primeiro fonema. Vale também para o cache de frases fixas.
- **Dicionário de pronúncia** em `ui/shared/keypad.py`, para as palavras que o motor ainda leia mal mesmo com o início preservado. A tela continua mostrando o rótulo de sempre, e só o texto falado muda.

### Decimais lidos com "vírgula" (T02) — **BREAKING na fala**

- O separador decimal passa a ser falado como "**vírgula**": `1.2` vira «1 vírgula 2». A parte fracionária continua lida dígito a dígito, para preservar zeros (`0.05` vira «0 vírgula 0 5»), e negativos continuam com "menos".
- O **separador de argumentos** (`,`, em `Pol(3,4)`) passa a ser falado como "**ponto e vírgula**". Se as duas vírgulas tivessem o mesmo nome, «Pol 3 vírgula 4» seria ambíguo com o decimal 3,4. É a mesma convenção das planilhas em pt-BR, onde a vírgula é decimal e o ponto e vírgula separa argumentos.
- A tecla `.` (ponto decimal) passa a ser anunciada como "vírgula", que é o que ela insere.
- **A tela não muda:** continua a mostrar o ponto. Trocar o separador visual é outra decisão (ver design, questões abertas).

### Abertura de parênteses nas funções (T03)

- Toda função com parênteses passa a anunciar a abertura: `sqrt(` vira «raiz quadrada, abre parênteses». Vale para a leitura da expressão (`Shift` + `Ans`) **e** para o retorno de tecla, porque as duas tinham de concordar.
- As leituras de par (polar e retangular) já estão padronizadas e só herdam a troca de "ponto" para "vírgula" (T02).

### Latência do resultado (T04)

- **Medir no Pi** quanto tempo vai para cada etapa: síntese, arranque do `aplay` e abertura do dispositivo.
- **Começar a falar antes de a frase inteira estar pronta:** o prefixo fixo («Resultado», «Última resposta») sai do cache enquanto o número é sintetizado. O número é sintetizado em pedaços, cada um tocado assim que fica pronto.
- O RF-08 continua valendo: um novo toque corta tudo, inclusive os pedaços ainda por tocar.

### Multiplicação implícita e o caso `2e3` (T07)

- **Multiplicação implícita:** um número, `)`, `π`, `e` ou `Ans` seguido de `(`, de uma função, de uma constante ou de `Ans` multiplica. `2(3)` dá 6, `2sqrt(9)` dá 6, `(2)(3)` dá 6 e `2π` dá 6,283….
- **`2e3` passa a ser 2×*e*×3.** Um literal em notação científica do Python nunca pode chegar ao `ast.parse`. A tecla `EXP` (×10ˣ) continua sendo a única forma de entrar com uma potência de dez.
- **Testes de regressão** com uma bateria de expressões comparadas com a calculadora de referência, incluindo os casos já corretos, para não regredirem.
- **Bloqueado até a equipe definir o modelo de referência:** a porcentagem depois de soma ou subtração (`50+10%`) e a prioridade da multiplicação implícita contra a divisão (`1÷2(3)`). Ver design.

### Números complexos: avaliação (T08)

- Registrar no design a avaliação pedida: o catálogo do PRD §5 lista apenas as conversões de coordenadas, já implementadas. Aritmética complexa, o literal `i`, módulo e argumento são funções novas e exigem revisão do escopo do TCC. Por isso, ficam fora desta change.

### Modo somente áudio (correção)

- `audio_only.py` passa a usar a mesma leitura de resultado dos fronts visuais, pares incluídos.

### Validação (T11)

- Testes para cada comportamento acima, mais a verificação no aparelho: escuta das palavras curtas, medição de latência antes e depois, e o conjunto de expressões de regressão comparado com a calculadora de referência.

## Não-objetivos

- **Não expandir o catálogo do PRD §5.** Multiplicação implícita é notação de entrada, não operação nova. Aritmética complexa (T08) fica fora, pelos motivos acima.
- **Não trocar a voz** `cadu` nem o motor Piper. Se a escuta (T01) reprovar a pronúncia mesmo sem o corte, trocar de voz é outra change.
- **Não mudar o separador decimal da tela** nesta change: muda só o que é falado.
- **Não decidir a semântica da porcentagem nem a prioridade da multiplicação implícita** sem o modelo de referência.
- **Não mexer na fiação** (T10): é acabamento físico, fora do software.
- **Não acoplar o motor de cálculo à UI.** A multiplicação implícita fica em `core/engine.py`, e tudo o que é falado fica em `ui/shared/` e `accessibility/`.

## Capabilities

### New Capabilities

- `spoken-feedback`: como números, teclas e expressões viram texto falado. Cobre o separador decimal "vírgula", o separador de argumentos "ponto e vírgula", o dicionário de pronúncia, o anúncio da abertura de parênteses e a mesma leitura de resultado nos dois fronts e no modo somente áudio.

### Modified Capabilities

- `coordinate-conversion`: o requisito "Leitura falada padronizada do par" troca "ponto" por "vírgula" nos exemplos fixados. O requisito "Os fronts falam pares pelo caminho padronizado" passa a cobrir explicitamente o modo somente áudio, onde hoje falha.
- `speech-engine`: novos requisitos de silêncio inicial (o início da fala não pode ser cortado) e de início antecipado (a fala de um resultado começa antes de a síntese terminar), mantendo a interrupção do RF-08.
- `expression-normalization`: novos requisitos de multiplicação implícita e de que um literal em notação científica nunca chega ao avaliador.

## Impact

**Código**

- `software/accessibility/speech.py`: silêncio inicial no PCM, e síntese e reprodução em pedaços com o prefixo fixo vindo do cache.
- `software/ui/shared/speech_text.py`: "vírgula" no decimal, e abertura de parênteses na leitura da expressão.
- `software/ui/shared/keypad.py`: dicionário de pronúncia, nomes falados de `.`, `,` e das funções com parênteses.
- `software/core/engine.py`: multiplicação implícita e neutralização do literal `2e3`.
- `software/audio_only.py`: leitura de resultado partilhada com os fronts.

**Testes a atualizar** (consequência do BREAKING na fala)

- `test_speech_text.py`, `test_pair_display.py` e `test_shift_ans_and_dot_key.py`: as asserções com "ponto" passam a "vírgula".
- Os testes que fixam o texto de uma tecla de função passam a esperar «…, abre parênteses».

**Documentação**

- `docs/guias/teclado-matriz.md` e `teclas-resumo.md` (o que cada tecla fala), PRD §13 (o exemplo de leitura dos números) e o mapa HTML do teclado.

**Hardware (Pi)**

- A causa da T01 e os ganhos da T04 só se confirmam no aparelho. As tarefas de medição vêm **antes** das correções de áudio.
