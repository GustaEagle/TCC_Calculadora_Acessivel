## 1. Medição no Pi antes de mexer no áudio (T01/T04)

- [ ] 1.1 Gravar no Pi a saída de áudio das teclas `AC`, `3`, `4`, `π`, `(` e `)` e comparar com o PCM entregue ao `aplay`, para decidir se o «impa tudo» é corte do início ou pronúncia. Verificar: conclusão registrada em `docs/testes/`.
- [ ] 1.2 Medir o tempo entre soltar o `=` e o primeiro som, para um resultado inteiro (`2+2`), um decimal longo (`1/7`) e um par (`polar(3,4)`). Verificar: números em `docs/testes/`.
- [ ] 1.3 Decompor o tempo de 1.2 em síntese, arranque do `aplay` e abertura do dispositivo, com logs de tempo provisórios no `_RawPlaybackProcess`. Verificar: a etapa dominante identificada e registrada.

## 2. Texto falado: vírgula, ponto e vírgula e abertura de parênteses (T02/T03) — BREAKING na fala

- [x] 2.1 Em `software/ui/shared/speech_text.py`, trocar "ponto" por "vírgula" em `spoken_number`, mantendo a parte fracionária dígito a dígito e o "menos" do sinal.
- [x] 2.2 Em `software/ui/shared/keypad.py`, mudar o nome falado de `.` para "vírgula" e o de `,` para "ponto e vírgula".
- [x] 2.3 No mesmo catálogo, acrescentar «, abre parênteses» ao nome falado de todo token terminado em `(` (`sqrt(`, `sen(`, `cos(`, `tan(`, `asin(`, `acos(`, `atan(`, `log(`, `ln(`, `logbase(`, `inv(`, `polar(`, `rect(`, `exp(`).
- [x] 2.4 Garantir que a leitura da expressão (`spoken_expression`) não duplica o «abre parênteses», ao ler o token de função como uma unidade.
- [x] 2.5 Criar `TTS_PRONUNCIATION` vazia em `keypad.py`, aplicada só ao texto entregue ao motor de voz, e preenchê-la apenas com o que a 1.1 confirmar como pronúncia (com motivo em comentário).
- [x] 2.6 Testes em `software/tests/test_speech_text.py`: `1.2`, `0.05`, `-3.5`, `.5`, `10`, `-7`, `3.14*2`, `polar(3,4)` e `polar(1.5,2)`, com os textos da spec `spoken-feedback`.
- [x] 2.7 Teste que percorre `SPOKEN_TOKEN_NAMES` e falha se algum token terminado em `(` não terminar com «, abre parênteses», ou se um token sem parênteses o tiver.
- [x] 2.8 Teste de que uma entrada em `TTS_PRONUNCIATION` muda o texto falado e não muda o rótulo nem o símbolo exibido.
- [x] 2.9 Atualizar as asserções que fixam "ponto": `test_speech_text.py`, `test_pair_display.py`, `test_shift_ans_and_dot_key.py`, e os testes de retorno de teclas de função.

## 3. Leitura de resultado partilhada, incluindo o modo somente áudio

- [x] 3.1 Extrair para `software/ui/shared/speech_text.py` uma função única de texto falado de um resultado (par ou escalar), substituindo os `_spoken_result` duplicados de `ui/lcd/app.py` e `ui/hdmi/app.py`.
- [x] 3.2 Usar essa função em `software/audio_only.py`, que hoje fala `spoken_number(result.display)` e lê a tupla com pontuação.
- [x] 3.3 Testes: o mesmo resultado escalar e o mesmo par produzem o mesmo texto nos três modos. `polar(3,4)` em modo somente áudio não contém `(`, `)` nem `,`.

## 4. Motor: multiplicação implícita e o caso `2e3` (T07)

- [x] 4.1 Em `software/core/engine.py`, desfazer `NeM` (número, `e`, dígitos) em `N*e*M` antes de o texto chegar ao `ast.parse`.
- [x] 4.2 Inserir `*` entre operando à esquerda (número, `)`, `pi`, `e`, valor de `Ans`) e operando à direita (`(`, função, `pi`, `e`), depois da canonicalização dos nomes e antes do fecho automático e da reescrita infixa, registrando a ordem em comentário.
- [x] 4.3 Garantir que o passo não insere `*` entre um nome de função e o seu `(`, não duplica a multiplicação implícita do `exp(` e não toca no `__ncr`/`__npr` internos.
- [x] 4.4 Novo `software/tests/test_implicit_multiplication.py` com os cenários da spec: `2(3)`, `2(3+4)`, `2sqrt(9)`, `(2)(3)`, `sqrt(4)(2)`, `2π`, `3Ans` (ans=4), `sin(30)`, `3exp(8)` e `5 nCr 2`.
- [x] 4.5 No mesmo ficheiro, o caso `2e3` → `16.30969097`, `1e5` → `13.59140914`, `2e` → `5.436563657`, `e^2` → `7.389056099` e `2exp(3)` → `2000`.
- [x] 4.6 Bateria de regressão em `software/tests/test_precedence_regression.py` com os casos que já estão certos: `2+3*4`, `2^3^2`, `2^2^3`, `-2^2`, `-(2)^2`, `2^-1`, `8/2/2`, `2-3-4`, `10-2*3`, `1/2*3`, `3!^2`, `sen(30)^2` e `2*(3+4)`.
- [x] 4.9 (descoberta na implementação) Trocar a substituição textual de `Ans` (`str(ans)`) por um nome protegido avaliado como constante: colar o valor fazia `Ans^2` com Ans = −3 dar −9 e exporia `1e+20` à multiplicação implícita. Reconhecer `Ans` colado a um número (`3Ans`). Atualizar o teste que fixava `Ans nCr 2` = −10 com Ans = −5, que passa a `ERR-004`.
- [ ] 4.7 **BLOQUEADA** até a equipe definir o modelo de referência: semântica da porcentagem depois de soma ou subtração (`50+10%`).
- [ ] 4.8 **BLOQUEADA** pelo mesmo motivo: prioridade da multiplicação implícita contra a divisão (`1÷2(3)`, `6÷2(1+2)`), com o teste correspondente.

## 5. Áudio: silêncio inicial e reprodução em pedaços (T01/T04)

- [x] 5.1 Em `software/accessibility/speech.py`, acrescentar `LEADING_SILENCE_MS` (começando em 120 ms e ajustado pela 1.1) e prefixar o PCM de cada frase no ponto único antes da escrita no `aplay`, valendo para o cache, o Piper e o `espeak-ng`.
- [x] 5.2 Testes com um motor e um `aplay` falsos: o PCM entregue começa pelas amostras nulas da duração configurada, também para frases do cache, e o silêncio aparece uma vez por frase.
- [x] 5.3 Ampliar o conjunto fechado do cache com os dígitos de 0 a 9, «vírgula», «ponto e vírgula», «menos», «Resultado», «Última resposta» e os rótulos dos pares, e aparar o silêncio final do PCM de cada pedaço ao aquecer.
- [x] 5.4 Reescrever a produção de uma frase para dividi-la em pedaços pelas fronteiras do conjunto fechado, tirar do cache o que existir e sintetizar o resto, escrevendo na stdin de **um** `aplay` em ordem, conforme cada pedaço fica pronto.
- [x] 5.5 Garantir que `terminate()` para a produtora e mata o `aplay`, descartando os pedaços pendentes (RF-08).
- [x] 5.6 Testes com um motor falso lento: o prefixo é entregue antes de o número terminar de ser sintetizado, a ordem da frase é mantida, só o cardinal inteiro vai à síntese, um único `aplay` é aberto por frase e a interrupção descarta o resto.

## 6. Números complexos (T08)

- [x] 6.1 Registrar na documentação (`docs/guias/teclado-matriz.md` ou PRD §5) a avaliação do design, decisão 7: aritmética complexa fica fora do catálogo, e só se abre uma change nova se o TCC rever o §5.

## 7. Documentação

- [x] 7.1 `docs/guias/teclado-matriz.md` e `teclas-resumo.md`: como os decimais e o separador são falados, a abertura de parênteses e a multiplicação implícita.
- [x] 7.2 PRD §13 e §14: o exemplo de leitura dos números passa a "vírgula"; registrar a mudança.
- [x] 7.3 Regenerar `docs/keyboard-layout/mapa-teclado.html` a partir do código, porque os nomes falados mudam.

## 8. Validação (T11)

- [x] 8.1 Correr a suite completa com as dependências gráficas e confirmar que passa inteira.
- [ ] 8.2 No Pi: repetir a 1.1 e confirmar que as palavras curtas soam inteiras.
- [ ] 8.3 No Pi: repetir a 1.2 e registrar o ganho de latência, comparando com o RNF-01 (~500 ms).
- [ ] 8.4 Escuta da equipe com resultados longos e pares: a montagem em pedaços soa fluente e os decimais com "vírgula" são claros.
- [ ] 8.5 Comparar a bateria de regressão da 4.6 com a calculadora de referência, quando definida, e registrar as divergências.
- [x] 8.6 Correr `openspec validate fix-speech-feedback-and-precedence --strict`.
