# coordinate-conversion Specification

## Purpose
TBD - created by archiving change fix-math-functions-and-help-key. Update Purpose after archive.
## Requirements
### Requirement: Pol converte para polar e devolve o par completo

A conversão **retangular → polar** (`Pol(x, y)`, token `polar(`) SHALL seguir a convenção das calculadoras científicas: o nome da tecla diz o **destino** da conversão. Recebe `(x, y)` e SHALL devolver **as duas componentes** polares, `(r, θ)`, com `r = hypot(x, y)` e `θ = atan2(y, x)`. SHALL NOT devolver apenas uma delas.

O ângulo `θ` SHALL ser convertido para a unidade do **modo angular ativo** (graus em `deg`, radianos em `rad`). O uso de `atan2` (e não `atan(y/x)`) SHALL garantir o quadrante correto e a ausência de divisão por zero quando `x = 0`.

O valor SHALL ser propagado em `CalculationResult.value` como `tuple[float, float]`.

#### Scenario: Conversão canónica em graus

- **WHEN** `evaluate("polar(3, 4)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(5.0, 53.13010235415598)` e `display` contém `5` e `53.13010235`

#### Scenario: Eixo vertical sem divisão por zero

- **WHEN** `evaluate("polar(0, 1)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 90.0)`, sem erro de divisão por zero

#### Scenario: Quadrante correto para x negativo

- **WHEN** `evaluate("polar(-1, 0)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(1.0, 180.0)`, e o ângulo SHALL NOT ser `0.0` nem `-0.0`

#### Scenario: Conversão em radianos

- **WHEN** `evaluate("polar(1, 1)")` é chamado com o modo angular em `rad`
- **THEN** `value` é o par `(1.4142135623730951, 0.7853981633974483)`

#### Scenario: Origem

- **WHEN** `evaluate("polar(0, 0)")` é chamado
- **THEN** `value` é o par `(0.0, 0.0)`

### Requirement: Rec converte para retangular e devolve o par completo

A conversão **polar → retangular** (`Rec(r, θ)`, token `rect(`) SHALL receber `(r, θ)` e devolver **as duas componentes** retangulares, `(x, y)`, com `x = r·cos(θ)` e `y = r·sin(θ)`, interpretando `θ` no **modo angular ativo**.

#### Scenario: Conversão em graus

- **WHEN** `evaluate("rect(2, 60)")` é chamado com o modo angular em `deg`
- **THEN** `value` é aproximadamente o par `(1.0, 1.7320508075688772)` e `display` contém `1` e `1.732050808`

#### Scenario: Ângulo nulo

- **WHEN** `evaluate("rect(1, 0)")` é chamado, em `deg` ou em `rad`
- **THEN** `value` é o par `(1.0, 0.0)`

#### Scenario: Raio nulo

- **WHEN** `evaluate("rect(0, 45)")` é chamado
- **THEN** `value` é o par `(0.0, 0.0)`

### Requirement: Pol e Rec são inversas uma da outra

Converter um ponto com `Pol` e devolver o resultado a `Rec` SHALL reproduzir o ponto original, e vice-versa, dentro da precisão do formato de exibição. Esta é a verificação que um utilizador faz à mão para decidir se as conversões estão certas.

#### Scenario: Ida e volta retangular → polar → retangular

- **WHEN** o resultado `(r, θ)` de `polar(3, 4)` é entregue a `rect(r, θ)`
- **THEN** o resultado é aproximadamente `(3.0, 4.0)`

#### Scenario: Ida e volta polar → retangular → polar

- **WHEN** o resultado `(x, y)` de `rect(2, 60)` é entregue a `polar(x, y)`
- **THEN** o resultado é aproximadamente `(2.0, 60.0)`

### Requirement: Ruído de vírgula flutuante é eliminado nos pares

Um componente de um par cujo módulo seja inferior a `1e-12` SHALL ser tratado como `0`, na **origem** (no motor), para que o valor, o texto da tela e a fala digam todos o mesmo. Sem isto, `sin(180°)` produziria `1.22e-16` e a voz leria o número dígito a dígito, com o expoente.

#### Scenario: Ângulo raso

- **WHEN** `evaluate("rect(1, 180)")` é chamado com o modo angular em `deg`
- **THEN** `value` é o par `(-1.0, 0.0)`, e a segunda componente SHALL ser exatamente `0.0`

### Requirement: Um par de coordenadas só é válido como expressão completa

Um resultado em par SHALL ser válido apenas quando a conversão for a **expressão inteira**. Usar uma conversão como operando de outra operação SHALL devolver `ERR-007` — o par tem duas componentes e não tem aritmética definida no catálogo do PRD §5. A restrição SHALL ser verificada explicitamente, e SHALL NOT escapar como erro interno de tipo.

#### Scenario: Conversão somada a um número

- **WHEN** `evaluate("polar(3, 4) + 1")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão aninhada noutra função

- **WHEN** `evaluate("sqrt(rect(2, 60))")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão como operando da combinação

- **WHEN** `evaluate("polar(3, 4) nCr 2")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão negada

- **WHEN** `evaluate("-polar(3, 4)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Conversão sozinha é válida

- **WHEN** `evaluate("polar(3, 4)")` é chamado
- **THEN** o resultado é bem-sucedido e `value` é um par

### Requirement: O sentido do par acompanha o resultado

`CalculationResult` SHALL transportar o **sentido** do par produzido, para que a camada de voz e de exibição escolham o formato correto sem reinterpretar a expressão. O sentido é o **destino** da conversão e SHALL ser determinado pelo nome da função no topo da expressão: `polar(` produz um par **polar**, `rect(` produz um par **retangular**. Um resultado escalar SHALL NOT ter sentido associado.

#### Scenario: Pol produz um par polar

- **WHEN** `evaluate("polar(3, 4)")` é bem-sucedido
- **THEN** o resultado identifica o par como coordenadas polares

#### Scenario: Rec produz um par retangular

- **WHEN** `evaluate("rect(2, 60)")` é bem-sucedido
- **THEN** o resultado identifica o par como coordenadas retangulares

#### Scenario: Resultado escalar sem sentido

- **WHEN** `evaluate("2+2")` é bem-sucedido
- **THEN** o resultado SHALL NOT identificar nenhum sentido, e a voz usa `spoken_number` como hoje

### Requirement: Dados insuficientes ou inválidos na conversão emitem ERR-009

Quando uma conversão for chamada com **mais** argumentos do que os dois exigidos, o motor SHALL devolver `ERR-009` ("Dados insuficientes ou inválidos para a conversão"), código já catalogado no PRD §13 e até então nunca emitido. O `ERR-009` SHALL ter prioridade **P1**, e a mensagem apresentada e falada SHALL ser a de `ERROR_MESSAGES["ERR-009"]`.

Com **menos** argumentos, o resultado é entrada incompleta: `ERR-008` (P2).

#### Scenario: Pol com argumentos a mais

- **WHEN** `evaluate("polar(5, 30, 2)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-009"` e prioridade `"P1"`

#### Scenario: Rec com argumentos a mais

- **WHEN** `evaluate("rect(3, 4, 5)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-009"`

#### Scenario: Conversão com um só argumento é expressão incompleta

- **WHEN** `evaluate("polar(5)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`

### Requirement: Leitura falada padronizada do par

Um par SHALL ser falado num formato fixo por sentido, com cada componente passando por `spoken_number` (separador decimal falado como "ponto" e parte fracionária dígito a dígito):

- par **retangular** (saída de `Rec`): «**x igual a [valor] e y igual a [valor]**»
- par **polar** (saída de `Pol`): «**real [valor], ângulo [valor]**»

O formato é fixo de propósito: quem não vê a tela só distingue as componentes pela frase.

#### Scenario: Par retangular com decimal

- **WHEN** o par `(1.0, 1.7320508075688772)` retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a 1 e y igual a 1 ponto 7 3 2 0 5 0 8 0 8"`

#### Scenario: Par retangular com componente negativa

- **WHEN** o par `(-1.0, 0.0)` retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a menos 1 e y igual a 0"`

#### Scenario: Par polar com decimal

- **WHEN** o par `(5.0, 53.13010235415598)` polar é falado
- **THEN** o texto entregue ao TTS é `"real 5, ângulo 53 ponto 1 3 0 1 0 2 3 5"`

#### Scenario: Par polar inteiro

- **WHEN** o par `(1.0, 90.0)` polar é falado
- **THEN** o texto entregue ao TTS é `"real 1, ângulo 90"`

### Requirement: Os fronts falam pares pelo caminho padronizado

Quando `CalculationResult.value` for uma tupla, cada front SHALL falar o resultado pela leitura de par do sentido correspondente, e SHALL NOT entregar o `display` da tupla a `spoken_number`, que o devolveria intacto e faria o motor neural ler a pontuação. O comportamento SHALL ser idêntico no front do LCD, no do monitor externo e no modo somente áudio (RF-04, RF-10).

#### Scenario: Par no front do LCD

- **WHEN** uma conversão é avaliada no front do LCD
- **THEN** o anúncio usa o formato padronizado do sentido do par, e SHALL NOT conter os caracteres `(`, `)` ou `,` lidos literalmente

#### Scenario: Par no front do monitor externo

- **WHEN** a mesma conversão é avaliada no front do monitor externo
- **THEN** o anúncio é o mesmo texto do front do LCD

### Requirement: Exibição do par em duas linhas rotuladas

Um par SHALL ser exibido na tela em **duas linhas rotuladas**, nunca como uma linha única com a tupla. Os rótulos acompanham o sentido: `r` e `θ` para um par polar, `x` e `y` para um retangular. Cada componente SHALL usar a mesma precisão do resultado escalar (`.10g`), para a tela não dizer menos do que a voz anuncia.

Um par numa só linha (`(5, 53.13010235)`, 16 caracteres) excedia o limite de resultado do LCD (14), e a truncagem, que mantinha a **cauda**, mostrava `..53.13010235)`: os `..` eram a marca do corte e o primeiro valor desaparecia por completo.

O display de um par SHALL usar corpo de fonte menor que o do resultado escalar, para duas linhas caberem na altura reservada. Qualquer linha truncada SHALL preservar a **cabeça**, pois num número a ordem de grandeza e os primeiros dígitos são o que importa, e cortar o início lê-se como outro número.

#### Scenario: Par polar em duas linhas

- **WHEN** o resultado de `polar(3, 4)` é exibido
- **THEN** o texto é `"r = 5\nθ = 53.13010235"`

#### Scenario: Par retangular em duas linhas

- **WHEN** o resultado de `rect(2, 60)` é exibido
- **THEN** o texto é `"x = 1\ny = 1.732050808"`

#### Scenario: Nenhum valor é cortado

- **WHEN** qualquer par de uma conversão válida é exibido
- **THEN** ambas as componentes estão presentes no texto e nenhuma linha contém a marca `..`

#### Scenario: Truncagem preserva a cabeça

- **WHEN** uma linha com `53364.75335` é cortada para 9 caracteres
- **THEN** o resultado é `53364.7..`

#### Scenario: Resultado escalar inalterado

- **WHEN** o resultado de `2+2` é exibido
- **THEN** o texto é `"4"`, na fonte e com o limite de sempre

