## ADDED Requirements

### Requirement: Conversão polar para retangular devolve o par completo

A função `polar(r, θ)` SHALL devolver **as duas componentes** retangulares, `(x, y)`, calculadas como `x = r·cos(θ)` e `y = r·sin(θ)`. SHALL NOT devolver apenas uma das componentes.

O valor SHALL ser propagado em `CalculationResult.value` como `tuple[float, float]` — tipo já previsto em `CalculationResult` — e o `display` SHALL apresentar as duas componentes.

#### Scenario: Conversão em graus

- **WHEN** `evaluate("polar(2, 60)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 1.7320508075688772)` e `display` contém as duas componentes `1` e `1.732050808`

#### Scenario: Ângulo nulo

- **WHEN** `evaluate("polar(1, 0)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 0.0)`

#### Scenario: Conversão em radianos

- **WHEN** `evaluate("polar(1, 0)")` é chamado com o modo angular em `rad`
- **THEN** `value` é o par `(1.0, 0.0)`, interpretando o segundo argumento como radianos

#### Scenario: Raio nulo

- **WHEN** `evaluate("polar(0, 45)")` é chamado
- **THEN** `value` é o par `(0.0, 0.0)`

### Requirement: Conversão retangular para polar devolve o par completo

A função `rect(x, y)` SHALL devolver **as duas componentes** polares, `(r, θ)`, com `r = hypot(x, y)` e `θ = atan2(y, x)`. SHALL NOT devolver apenas o raio.

O ângulo `θ` SHALL ser convertido para a unidade do **modo angular ativo** (graus em `deg`, radianos em `rad`), tal como o restante das funções trigonométricas do motor. O uso de `atan2` (e não `atan(y/x)`) SHALL garantir o quadrante correto e a ausência de divisão por zero quando `x = 0`.

#### Scenario: Conversão canónica em graus

- **WHEN** `evaluate("rect(3, 4)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(5.0, 53.13010235415598)` e `display` contém `5` e `53.13010235`

#### Scenario: Eixo vertical sem divisão por zero

- **WHEN** `evaluate("rect(0, 1)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 90.0)`, sem erro de divisão por zero

#### Scenario: Quadrante correto para x negativo

- **WHEN** `evaluate("rect(-1, 0)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 180.0)`, e SHALL NOT ser `0.0` nem `-0.0` no ângulo

#### Scenario: Conversão em radianos

- **WHEN** `evaluate("rect(1, 1)")` é chamado com o modo angular em `rad`
- **THEN** `value` é o par `(1.4142135623730951, 0.7853981633974483)`

#### Scenario: Origem

- **WHEN** `evaluate("rect(0, 0)")` é chamado
- **THEN** `value` é o par `(0.0, 0.0)`

### Requirement: Um par de coordenadas só é válido como expressão completa

Um resultado em par SHALL ser válido apenas quando a conversão for a **expressão inteira**. Usar uma conversão como operando de outra operação SHALL devolver `ERR-007`, com mensagem que indique expressão inválida — o par tem duas componentes e não tem aritmética definida no catálogo do PRD §5.

Esta restrição SHALL ser verificada explicitamente, e SHALL NOT escapar como erro interno de tipo.

#### Scenario: Conversão somada a um número

- **WHEN** `evaluate("polar(2, 60) + 1")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão aninhada noutra função

- **WHEN** `evaluate("sqrt(rect(3, 4))")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão como operando da combinação

- **WHEN** `evaluate("rect(3, 4) nCr 2")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão sozinha é válida

- **WHEN** `evaluate("rect(3, 4)")` é chamado
- **THEN** o resultado é bem-sucedido e `value` é um par

### Requirement: O sentido da conversão acompanha o resultado

`CalculationResult` SHALL transportar o **sentido** da conversão que produziu o par, para que a camada de voz escolha a frase padronizada correta sem reinterpretar a expressão. O sentido SHALL ser determinado pelo nome da função no topo da expressão — bem definido porque um par só é válido como expressão completa.

Um resultado escalar SHALL NOT ter sentido de conversão associado.

#### Scenario: Par retangular identificado

- **WHEN** `evaluate("polar(2, 60)")` é bem-sucedido
- **THEN** o resultado identifica o par como coordenadas retangulares

#### Scenario: Par polar identificado

- **WHEN** `evaluate("rect(3, 4)")` é bem-sucedido
- **THEN** o resultado identifica o par como coordenadas polares

#### Scenario: Resultado escalar sem sentido de conversão

- **WHEN** `evaluate("2+2")` é bem-sucedido
- **THEN** o resultado SHALL NOT identificar nenhum sentido de conversão, e a voz usa `spoken_number` como hoje

### Requirement: Dados insuficientes ou inválidos na conversão emitem ERR-009

Quando uma conversão de coordenadas for chamada com **número de argumentos diferente de dois**, o motor SHALL devolver `ERR-009` ("Dados insuficientes ou inválidos para a conversão"), código já catalogado no PRD §13 e até agora nunca emitido.

O `ERR-009` SHALL ter prioridade **P1** e a mensagem apresentada na UI e falada pelo TTS SHALL ser a mesma já registada em `ui/shared/error_messages.py`, conforme o RF-07.

#### Scenario: Conversão polar com argumentos a mais

- **WHEN** `evaluate("polar(5, 30, 2)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-009"` e prioridade `"P1"`

#### Scenario: Conversão retangular com argumentos a mais

- **WHEN** `evaluate("rect(3, 4, 5)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-009"`

#### Scenario: Mensagem coerente entre UI e voz

- **WHEN** um resultado de erro com `code` `"ERR-009"` é apresentado
- **THEN** o texto exibido e o texto falado derivam da mesma entrada `ERROR_MESSAGES["ERR-009"]`, e o anúncio falado é prefixado por `"Erro"` por ser um código `ERR-xxx` (P1)

#### Scenario: Conversão com um só argumento é expressão incompleta

- **WHEN** `evaluate("polar(5)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`, por ser entrada incompleta e não dado inválido

### Requirement: Leitura falada padronizada do resultado retangular

Um resultado em coordenadas **retangulares** (saída de `polar(...)`) SHALL ser falado no formato fixo **«x igual a [valor] e y igual a [valor]»**.

Cada componente SHALL passar pela conversão `spoken_number` já existente, de modo que o separador decimal seja falado como "ponto" e a parte fracionária lida dígito a dígito.

#### Scenario: Leitura de par retangular com decimal

- **WHEN** o resultado `(1.0, 1.7320508075688772)` de uma conversão polar → retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a 1 e y igual a 1 ponto 7 3 2 0 5 0 8 0 8"`

#### Scenario: Leitura de par retangular inteiro

- **WHEN** o resultado `(1.0, 0.0)` de uma conversão polar → retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a 1 e y igual a 0"`

#### Scenario: Componente negativa

- **WHEN** o resultado `(-1.0, 0.0)` de uma conversão polar → retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a menos 1 e y igual a 0"`

### Requirement: Leitura falada padronizada do resultado polar

Um resultado em coordenadas **polares** (saída de `rect(...)`) SHALL ser falado no formato fixo **«real [valor], ângulo [valor]»**, com as mesmas regras de `spoken_number` por componente.

#### Scenario: Leitura de par polar com decimal

- **WHEN** o resultado `(5.0, 53.13010235415598)` de uma conversão retangular → polar é falado
- **THEN** o texto entregue ao TTS é `"real 5, ângulo 53 ponto 1 3 0 1 0 2 3 5"`

#### Scenario: Leitura de par polar inteiro

- **WHEN** o resultado `(1.0, 90.0)` de uma conversão retangular → polar é falado
- **THEN** o texto entregue ao TTS é `"real 1, ângulo 90"`

### Requirement: Os fronts falam pares pelo caminho padronizado

Quando `CalculationResult.value` for uma tupla, cada front SHALL falar o resultado pela conversão de par correspondente ao sentido da conversão, e SHALL NOT entregar o `display` da tupla a `spoken_number` — que devolveria a string intacta e faria o motor neural ler a pontuação em voz alta.

O comportamento SHALL ser idêntico no front do LCD, no front do monitor externo e no modo somente áudio (RF-04, RF-10).

#### Scenario: Resultado em par no front do LCD

- **WHEN** uma conversão de coordenadas é avaliada no front do LCD
- **THEN** o anúncio falado usa o formato padronizado do sentido da conversão, e SHALL NOT conter os caracteres `(`, `)` ou `,` lidos literalmente

#### Scenario: Resultado em par no front do monitor externo

- **WHEN** a mesma conversão é avaliada no front do monitor externo
- **THEN** o anúncio falado é o mesmo texto do front do LCD

#### Scenario: Resultado em par em modo somente áudio

- **WHEN** a mesma conversão é avaliada com o sistema em `DisplayMode.AUDIO_ONLY`
- **THEN** o anúncio falado é o mesmo texto, mantendo o catálogo de operações sem redução (RF-10)
