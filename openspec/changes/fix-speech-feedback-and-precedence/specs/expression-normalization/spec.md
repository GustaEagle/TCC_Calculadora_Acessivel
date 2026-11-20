## ADDED Requirements

### Requirement: Multiplicação implícita

Um operando seguido **imediatamente** de outro operando SHALL ser lido como multiplicação, como numa calculadora comercial (T07). Conta como operando à esquerda: número, `)`, `π`/`pi`, `e` e `Ans` já substituído. Conta como operando à direita: `(`, chamada de função, `π`/`pi`, `e` e `Ans`.

A multiplicação implícita SHALL NOT mudar o significado de nomes de função (`sin(30)` continua a ser uma chamada), da tecla `EXP` (`3exp(8)` continua 3×10⁸), dos operadores infixos (`5 nCr 2` continua 10) nem do fecho automático de parênteses.

A **prioridade** da multiplicação implícita em relação à divisão explícita (`1÷2(3)`) **não é fixada por este requisito**. Depende do modelo de calculadora de referência, que a equipe ainda vai definir.

#### Scenario: Número seguido de parênteses

- **WHEN** `evaluate("2(3)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"6"`

#### Scenario: Número seguido de grupo com operação

- **WHEN** `evaluate("2(3+4)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"14"`

#### Scenario: Número seguido de função

- **WHEN** `evaluate("2sqrt(9)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"6"`

#### Scenario: Grupo seguido de grupo

- **WHEN** `evaluate("(2)(3)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"6"`

#### Scenario: Função seguida de grupo

- **WHEN** `evaluate("sqrt(4)(2)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"4"`

#### Scenario: Número seguido de constante

- **WHEN** `evaluate("2π")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"6.283185307"`

#### Scenario: Número seguido de Ans

- **WHEN** `evaluate("3Ans", ans=4)` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"12"`

#### Scenario: Função sem multiplicação implícita espúria

- **WHEN** `evaluate("sin(30)")` é chamado com o modo angular em `deg`
- **THEN** o resultado é bem-sucedido com `display` igual a `"0.5"`

#### Scenario: Tecla EXP e nCr inalterados

- **WHEN** `evaluate("3exp(8)")` e `evaluate("5 nCr 2")` são chamados
- **THEN** os resultados são `"300000000"` e `"10"`

### Requirement: Um literal em notação científica nunca chega ao avaliador

Um número seguido da letra `e` e de dígitos (`2e3`, `1e5`) SHALL ser lido como **multiplicação pela constante de Euler**, e SHALL NOT ser interpretado como notação científica do Python. Quem pressiona `2`, `e`, `3` quer 2×*e*×3. Hoje recebe 2000 sem aviso: é um resultado errado e silencioso. A tecla `EXP` (×10ˣ) SHALL continuar a ser a única forma de entrar com uma potência de dez.

#### Scenario: O caso relatado

- **WHEN** `evaluate("2e3")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"16.30969097"` (2×e×3), e SHALL NOT ser `"2000"`

#### Scenario: Outro literal com expoente

- **WHEN** `evaluate("1e5")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"13.59140914"` (1×e×5), e SHALL NOT ser `"100000"`

#### Scenario: Número seguido só da constante

- **WHEN** `evaluate("2e")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"5.436563657"`

#### Scenario: Potência de e inalterada

- **WHEN** `evaluate("e^2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"7.389056099"`

#### Scenario: Potência de dez pela tecla EXP

- **WHEN** `evaluate("2exp(3)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"2000"`
