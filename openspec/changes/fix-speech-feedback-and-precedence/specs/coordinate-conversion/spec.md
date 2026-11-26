## MODIFIED Requirements

### Requirement: Leitura falada padronizada do par

Um par SHALL ser falado num formato fixo por sentido, com cada componente passando por `spoken_number` (separador decimal falado como "vírgula" e parte fracionária dígito a dígito, ver a capacidade `spoken-feedback`):

- par **retangular** (saída de `Rec`): «**x igual a [valor] e y igual a [valor]**»
- par **polar** (saída de `Pol`): «**real [valor], ângulo [valor]**»

O formato é fixo de propósito: quem não vê a tela só distingue as componentes pela frase.

#### Scenario: Par retangular com decimal

- **WHEN** o par `(1.0, 1.7320508075688772)` retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a 1 e y igual a 1 vírgula 7 3 2 0 5 0 8 0 8"`

#### Scenario: Par retangular com componente negativa

- **WHEN** o par `(-1.0, 0.0)` retangular é falado
- **THEN** o texto entregue ao TTS é `"x igual a menos 1 e y igual a 0"`

#### Scenario: Par polar com decimal

- **WHEN** o par `(5.0, 53.13010235415598)` polar é falado
- **THEN** o texto entregue ao TTS é `"real 5, ângulo 53 vírgula 1 3 0 1 0 2 3 5"`

#### Scenario: Par polar inteiro

- **WHEN** o par `(1.0, 90.0)` polar é falado
- **THEN** o texto entregue ao TTS é `"real 1, ângulo 90"`

### Requirement: Os fronts falam pares pelo caminho padronizado

Quando `CalculationResult.value` for uma tupla, cada front SHALL falar o resultado pela leitura de par do sentido correspondente, e SHALL NOT entregar o `display` da tupla a `spoken_number`, que o devolveria intacto e faria o motor neural ler a pontuação. O comportamento SHALL ser idêntico no front do LCD, no do monitor externo e no modo somente áudio (RF-04, RF-10). O modo somente áudio SHALL usar a mesma função de leitura de resultado dos fronts visuais, e não uma cópia própria.

#### Scenario: Par no front do LCD

- **WHEN** uma conversão é avaliada no front do LCD
- **THEN** o anúncio usa o formato padronizado do sentido do par, e SHALL NOT conter os caracteres `(`, `)` ou `,` lidos literalmente

#### Scenario: Par no front do monitor externo

- **WHEN** a mesma conversão é avaliada no front do monitor externo
- **THEN** o anúncio é o mesmo texto do front do LCD

#### Scenario: Par no modo somente áudio

- **WHEN** a mesma conversão é avaliada no modo somente áudio
- **THEN** o anúncio é o mesmo texto do front do LCD, e o resultado SHALL NOT ser lido a partir do `display` da tupla
