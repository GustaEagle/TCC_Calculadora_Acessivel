## Context

Pipeline de voz hoje, para uma frase:

1. o front monta o texto (`"Resultado " + spoken_number(...)`) e chama `interrupt_and_say`;
2. o worker de fala cria um `_RawPlaybackProcess`, que chama `_produce(text)`: o cache, se a frase **inteira** estiver lá, senão o Piper, senão o `espeak-ng`;
3. só depois de a síntese da frase completa terminar, abre um processo **novo** de `aplay` e escreve o PCM na stdin.

Três propriedades desse desenho explicam as queixas do teste:

- **Nada soa antes de a frase inteira estar sintetizada.** Com o decimal lido dígito a dígito, «Resultado 1 ponto 7 3 2 0 5 0 8 0 8» é uma frase longa, e o tempo de síntese cresce com ela (T04).
- **O dispositivo de áudio é aberto a frio a cada frase.** Saídas HDMI e alguns codecs descartam os primeiros milissegundos de um fluxo novo. É compatível com o «**impa** tudo» (T01): o texto entregue ao motor é «limpar tudo», e perde-se exatamente o primeiro fonema. Palavras curtas (`3`, `4`, `π`) são as mais afetadas porque o corte come uma fração maior delas.
- **O cache só serve frases inteiras.** «Resultado» está no conjunto fechado, mas «Resultado 10» não. O cache nunca é usado para resultados, que são justamente o caso do `=`.

No motor de cálculo, a normalização por regex nunca insere multiplicação implícita, e um número colado ao `e` (`2e3`) sobrevive até ao `ast.parse`, que o lê como literal científico do Python.

Restrições:

- RF-08: nenhuma fala bloqueia a entrada, e um novo toque corta a fala em curso.
- RNF-01 (~500 ms de resposta perceptível) e RNF-02 (latência de TTS aceitável, offline).
- O motor (`core/`) não importa UI.
- O catálogo do PRD §5 é fechado.

## Goals / Non-Goals

**Goals:**

- Fazer a primeira sílaba de toda frase soar.
- Começar a falar o resultado no menor tempo possível depois do `=`, idealmente com o prefixo saindo do cache imediatamente.
- Ler decimais em pt-BR sem ambiguidade com o separador de argumentos.
- Anunciar a abertura de parênteses das funções.
- Fazer o motor aceitar a notação de calculadora comercial (multiplicação implícita) e eliminar o resultado silenciosamente errado de `2e3`.
- **Medir antes de corrigir** o que só o aparelho confirma.

**Non-Goals:**

- Trocar a voz ou o motor de síntese.
- Mudar o separador decimal **visual**.
- Fixar a semântica da porcentagem e a prioridade da multiplicação implícita contra a divisão, que estão bloqueadas pelo modelo de referência.
- Aritmética complexa (T08, ver decisão 7).

## Decisions

### 1. Silêncio inicial no PCM, e não um `aplay` persistente

Antes do áudio de cada frase entra uma constante `LEADING_SILENCE_MS` de amostras nulas, com valor de partida de 120 ms, a ajustar na medição. O silêncio é acrescentado no ponto único por onde passa todo o PCM, antes da escrita no `aplay`, de modo que cobre o cache, o Piper e o `espeak-ng` sem tocar em cada um.

*Alternativa considerada:* um `aplay` residente, que nunca fecha o dispositivo. Elimina o arranque a frio pela raiz, mas a interrupção do RF-08 funciona hoje **matando** o `aplay`. Um processo residente exigiria outro mecanismo de corte, como descartar o buffer do ALSA, com risco de deixar áudio já enfileirado tocando depois do corte. O silêncio resolve o sintoma com uma linha e sem tocar na interrupção. Se a medição mostrar que não basta, o `aplay` residente fica como próximo passo.

*Alternativa considerada:* corrigir a pronúncia com grafias alternativas («limpa tudo»). Trataria o sintoma palavra a palavra, e a próxima palavra curta voltaria a falhar. O dicionário de pronúncia (decisão 4) fica reservado ao que a escuta mostrar que é **pronúncia**, e não corte.

### 2. Reprodução em pedaços num único `aplay`, com o cache por palavra

A frase é dividida em pedaços. Uma thread produtora entrega-os em ordem a um único `aplay`, escrevendo na stdin conforme cada pedaço fica pronto. O `aplay` toca o que já recebeu enquanto o resto é sintetizado. A interrupção continua a ser matar o `aplay` e parar a produtora, então os pedaços pendentes descartam-se sozinhos.

A divisão segue o conjunto fechado do cache: todo pedaço que estiver no cache sai dele sem síntese. O ganho maior vem de a parte fracionária ser lida **dígito a dígito**. Cada dígito é uma palavra isolada, e por isso «7 3 2 0 5 0 8 0 8» monta-se inteiramente do cache, junto com «Resultado», «vírgula», «menos» e os rótulos dos pares. Só a parte inteira (o cardinal «53») e palavras fora do conjunto vão ao Piper.

O conjunto fechado do cache passa a incluir os dígitos de 0 a 9, «vírgula», «ponto e vírgula», «menos», «Resultado», «Última resposta» e os rótulos dos pares.

*Alternativa considerada:* duas mensagens na fila, `interrupt_and_say("Resultado")` e depois `say(número)`. Não ganha nada: o worker só sintetiza uma mensagem quando a anterior acaba de tocar, e reabriria o dispositivo entre as duas, o que reintroduz o corte da decisão 1.

*Alternativa considerada:* sintetizar a frase inteira palavra a palavra. Para cardinais longos e texto corrido a prosódia pioraria. A divisão é por fronteiras que já são pausas naturais (o prefixo, cada dígito lido isolado e as palavras de rótulo).

*Risco conhecido:* o Piper põe silêncio no fim de cada trecho, e a concatenação pode deixar pausas longas entre dígitos. Mitigação: aparar o silêncio final do PCM de cada pedaço do cache ao aquecê-lo, e validar numa escuta (tarefas).

### 3. "Vírgula" no decimal e "ponto e vírgula" no separador

`spoken_number` troca "ponto" por "vírgula". A tecla `.` passa a ser falada "vírgula" e a `,` (separador de argumentos) "ponto e vírgula". É a convenção das planilhas em pt-BR, onde a vírgula é o decimal e o ponto e vírgula separa argumentos. Sem a troca do separador, «Pol 3 vírgula 4» seria ambíguo com o decimal 3,4, e o produto é operado de ouvido.

A **tela** continua com `.`: trocar o símbolo visual mexe na digitação e nos testes de layout, e não foi pedido (questão aberta).

### 4. O nome falado é o mesmo na tecla e na expressão

A abertura de parênteses é acrescentada no **catálogo** (`SPOKEN_TOKEN_NAMES`). Por exemplo, `sqrt(` passa a ser «raiz quadrada, abre parênteses». Assim o retorno da tecla e a leitura da expressão usam a mesma fonte e não podem divergir, exatamente como a consulta da tecla `?` já depende do catálogo.

Um teste percorre o catálogo e falha se algum token terminado em `(` não terminar com «, abre parênteses».

O dicionário de pronúncia é uma tabela à parte, `TTS_PRONUNCIATION`, aplicada **só** ao texto entregue ao motor de voz. Começa vazia e só recebe entradas que a escuta no aparelho confirmar, cada uma com o motivo em comentário.

*Custo aceite:* o retorno das teclas de função fica mais longo («raiz quadrada, abre parênteses»). A interrupção do RF-08 mantém a digitação rápida possível, porque o toque seguinte corta a frase.

### 5. Multiplicação implícita como inserção de `*` na normalização

Um passo novo de `_normalize` insere `*` entre um operando à esquerda (número, `)`, `pi`, `e`, valor de `Ans` já substituído) e um operando à direita (`(`, identificador de função, `pi`, `e`). Corre **depois** da canonicalização dos nomes de função, para que `sin(` seja reconhecido como chamada, e **antes** do fecho automático e da reescrita infixa de `nCr`, para não interferir com elas.

Inserir `*` dá à multiplicação implícita a **mesma** prioridade da explícita, avaliada da esquerda para a direita. É o comportamento do Casio fx-82MS. Como essa prioridade está **bloqueada** à espera do modelo de referência, o teste correspondente fica **fora** desta change. Se a equipe escolher o fx-82ES (implícita com prioridade maior), troca-se o `*` por um agrupamento `(a*b)`, sem mexer no resto.

Cuidados que os testes fixam:

- um identificador seguido de `(` é chamada, não multiplicação;
- o `exp(` da tecla `EXP` já tem a sua multiplicação implícita, e o passo novo não a duplica;
- o `__ncr` interno não é um identificador sujeito ao passo, porque a reescrita infixa corre depois.

### 6. `2e3` deixa de ser literal científico

Antes da inserção da multiplicação implícita, um número imediatamente seguido de `e` e de dígitos é desfeito em `número * e * dígitos`. Na prática a decisão 5 cobre o caso, desde que corra antes de o texto chegar ao `ast.parse`, porque `2e3` passa a ser `2*e*3`.

O motivo de tratar `e` como constante e nunca como expoente: no teclado, a constante de Euler é uma **tecla**, e a potência de dez tem a sua tecla própria (`EXP`). Nada na interface produz notação científica do Python de propósito, então todo `NeM` que chega ao motor é a constante.

### 7. T08: aritmética complexa fica fora

A avaliação pedida na T08 conclui que o PRD §5 lista apenas **conversões de coordenadas**, já entregues. Os candidatos restantes são funções novas do catálogo: o literal `i`, soma e produto de complexos, módulo, argumento e conjugado. Sem a forma `a+bi` não há como representar o resultado na interface atual, cujo display de par já ocupa duas linhas. Recomendação registrada: só abrir uma change de aritmética complexa se o TCC rever o §5.

## Risks / Trade-offs

- **[A causa do «impa tudo» pode não ser o corte]** → A primeira tarefa é gravar a saída no Pi e comparar o PCM entregue com o som que sai. Se o fonema estiver no PCM e sair, a causa é a pronúncia, e entra o dicionário. A ordem das tarefas impede corrigir às cegas.
- **[Pausas entre pedaços concatenados]** → Aparar o silêncio final dos pedaços do cache, mais uma escuta da equipe com resultados longos. Se a fluência piorar de forma inaceitável, cai-se para sintetizar só o número inteiro, mantendo o prefixo do cache, que já elimina a espera inicial.
- **[BREAKING na fala: "ponto" passa a "vírgula"]** → A spec `coordinate-conversion` e os testes que fixam "ponto" são atualizados nesta change. A documentação (`teclado-matriz.md`) e o PRD §13 também mudam. A mudança é só falada, e nenhum dado persistido depende dela.
- **[Multiplicação implícita muda o significado de entradas que hoje dão erro]** → `2(3)` passava de `ERR-007` a 6. Ninguém dependia do erro, e a bateria de regressão fixa os casos válidos de hoje para não mudarem.
- **[`2e3` passa de 2000 a 16,31]** → É a correção, mas é uma mudança de valor. O teste regista-a explicitamente com o motivo.
- **[Retorno de tecla mais longo nas funções]** → Coberto pela interrupção do RF-08. A escuta valida se incomoda.

## Migration Plan

1. **Medição no Pi** (antes de qualquer mudança de áudio): gravar as palavras curtas, medir o tempo do `=` até o primeiro som e decompô-lo em síntese, arranque do `aplay` e abertura do dispositivo. Registrar em `docs/testes/`.
2. **Texto falado** (`speech_text.py`, `keypad.py`): vírgula, ponto e vírgula e abertura de parênteses. Atualizar os testes e as specs que fixam "ponto".
3. **Leitura partilhada** do resultado, incluindo o modo somente áudio.
4. **Motor**: multiplicação implícita e o caso `2e3`, com a bateria de regressão.
5. **Áudio** (`speech.py`): silêncio inicial, depois pedaços com cache por palavra.
6. **Validação no Pi**: repetir as medições do passo 1, fazer a escuta e comparar com a calculadora de referência.

**Rollback:** cada passo é independente. O silêncio inicial e os pedaços desligam-se pelas constantes (`LEADING_SILENCE_MS = 0`, divisão desligada) sem reverter código.

## Open Questions

- **Modelo da calculadora de referência** (bloqueia a porcentagem e a prioridade da multiplicação implícita):
  - Com o fx-82MS, `50+10%` = 55, e `1÷2(3)` = 1,5, da esquerda para a direita.
  - Com o fx-82ES/991ES, `50+10%` = 50,1 (o comportamento atual), e `1÷2(3)` = 0,1667, com a implícita primeiro.
- **Duração do silêncio inicial:** 120 ms é palpite. Sai da medição.
- **Separador decimal da tela:** se a equipe quiser `1,2` também no display, é uma change à parte, porque mexe na digitação.
- **Teclas `3`, `4` e `π`:** a queixa diz que soam mal, sem dizer como. A escuta de bancada esclarece se é o corte ou a pronúncia.
