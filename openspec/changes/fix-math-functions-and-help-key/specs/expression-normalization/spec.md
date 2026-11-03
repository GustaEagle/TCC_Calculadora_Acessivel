## ADDED Requirements

### Requirement: Fecho automático de parênteses inequívocos

Quando a expressão submetida tiver mais abre-parênteses que fecha-parênteses e **nenhum** fecha-parênteses órfão, o motor SHALL acrescentar os fecha-parênteses em falta antes de avaliar, produzindo o resultado como se o utilizador os tivesse digitado. O fecho SHALL ser aplicado **depois** de todas as reescritas de normalização, para contabilizar os parênteses que o próprio motor introduz (fatorial, percentagem, `logbase`).

A expressão original digitada pelo utilizador SHALL ser preservada em `CalculationResult.expression`; o fecho é um detalhe da avaliação e não reescreve o que está na linha de cálculo.

#### Scenario: Função científica sem fecho

- **WHEN** `evaluate("sqrt(144")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"12"`, e `expression` continua a ser `"sqrt(144"`

#### Scenario: Grupo aritmético sem fecho

- **WHEN** `evaluate("(2+3")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"5"`

#### Scenario: Vários níveis em falta

- **WHEN** `evaluate("sqrt((4")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"2"`, com os dois fecha-parênteses acrescentados

#### Scenario: Défice parcial numa expressão aninhada

- **WHEN** `evaluate("sqrt(16)+(2*3")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`, fechando apenas o grupo pendente e deixando o grupo já fechado intacto

#### Scenario: Expressão já equilibrada não é alterada

- **WHEN** `evaluate("sqrt(144)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"12"`, idêntico ao comportamento anterior à mudança

#### Scenario: Fecho atravessa a normalização de percentagem

- **WHEN** `evaluate("(50%")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"0.5"`, contabilizando os parênteses que a reescrita da percentagem introduziu

### Requirement: Fecha-parênteses órfão continua a ser erro de sintaxe

Quando a expressão contiver um fecha-parênteses **sem abertura correspondente**, o motor SHALL NOT tentar corrigir a expressão e SHALL devolver o erro `ERR-007` (prioridade P1). Um fecho órfão não tem leitura única e corrigi-lo por adivinhação seria pior que recusar.

#### Scenario: Fecho sem abertura

- **WHEN** `evaluate("2+)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"` e prioridade `"P1"`

#### Scenario: Fechos a mais depois de um grupo válido

- **WHEN** `evaluate("sqrt(4))")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Fecho órfão antes de um grupo pendente

- **WHEN** `evaluate(")2+(3")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`, e o fecho automático SHALL NOT ser aplicado apesar de existir um abre-parênteses pendente

### Requirement: Argumentos em falta são expressão incompleta, não inválida

Quando, após o fecho automático, uma função do catálogo ficar com **menos argumentos** do que exige, o motor SHALL devolver `ERR-008` ("Expressão incompleta") com prioridade **P2**, em vez de deixar escapar o `TypeError` da chamada como `ERR-007`. O catálogo de erros do PRD §13 distingue entrada incompleta (P2) de entrada sintaticamente inválida (P1), e a mensagem falada SHALL seguir essa distinção.

#### Scenario: Conversão com um só argumento após fecho automático

- **WHEN** `evaluate("polar(5")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`

#### Scenario: Logaritmo de base sem o segundo argumento

- **WHEN** `evaluate("logbase(2")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`

#### Scenario: Expressão vazia continua incompleta

- **WHEN** `evaluate("")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`, mantendo o comportamento já existente

### Requirement: Combinação e permutação em notação infixa

O motor SHALL aceitar `nCr` e `nPr` como operadores **infixos** entre dois operandos — `5 nCr 2` — e SHALL reescrevê-los internamente para as chamadas `ncr(n,r)` / `npr(n,r)` antes de avaliar. O reconhecimento SHALL ser insensível a maiúsculas/minúsculas e a espaços em volta do operador.

Um operando SHALL ser um átomo: número, constante (`pi`, `e`), `Ans` já substituído, grupo entre parênteses, ou uma chamada de função. Para agrupar qualquer outra coisa como operando, o utilizador SHALL usar parênteses explícitos.

A precedência SHALL ser **superior** à de `+` e `-`.

#### Scenario: Combinação pela sequência do teclado físico

- **WHEN** `evaluate("5 nCr 2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

#### Scenario: Combinação sem espaços

- **WHEN** `evaluate("5nCr2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

#### Scenario: Permutação pela sequência do teclado físico

- **WHEN** `evaluate("5 nPr 2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"20"`

#### Scenario: Insensível a maiúsculas

- **WHEN** `evaluate("5 NCR 2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

#### Scenario: Precedência acima da adição

- **WHEN** `evaluate("2 + 5 nCr 2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"12"`, calculando a combinação antes da soma

#### Scenario: Grupo entre parênteses como operando

- **WHEN** `evaluate("(4+1) nCr (1+1)")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

#### Scenario: Resposta anterior como operando

- **WHEN** `evaluate("Ans nCr 2", ans=5)` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

#### Scenario: Combinação encadeada com outra função

- **WHEN** `evaluate("sqrt(25) nCr 2")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"10"`

### Requirement: Limites e domínio da combinação e da permutação

O motor SHALL devolver `ERR-004` quando os operandos de `nCr`/`nPr` forem negativos, não inteiros, ou quando `n < r` — mantendo a regra de domínio já definida no PRD §13 — e SHALL aceitar os casos de limite válidos.

#### Scenario: n igual a r

- **WHEN** `evaluate("5 nCr 5")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"1"`

#### Scenario: r igual a zero

- **WHEN** `evaluate("5 nCr 0")` é chamado
- **THEN** o resultado é bem-sucedido com `display` igual a `"1"`

#### Scenario: n menor que r

- **WHEN** `evaluate("2 nCr 5")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-004"`

#### Scenario: Operando negativo

- **WHEN** `evaluate("5 nCr -2")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-004"`

#### Scenario: Operando não inteiro

- **WHEN** `evaluate("5.5 nCr 2")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-004"`

#### Scenario: Operando em falta

- **WHEN** `evaluate("5 nCr")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-008"` e prioridade `"P2"`

### Requirement: A forma funcional de nCr e nPr deixa de ser aceita

O motor SHALL NOT aceitar `nCr(n,r)` nem `nPr(n,r)` como chamadas de função. **BREAKING:** a notação infixa é a única forma válida; a forma funcional SHALL devolver `ERR-007`.

A tecla `nCr` SHALL inserir o token infixo `nCr` como função primária e `nPr` como função de `Ctrl`, de modo que a sequência física `5`, `nCr`, `2`, `=` produza a expressão `5 nCr 2`. Os tokens `nCr(` / `nPr(` SHALL ser removidos da lista de tokens que abrem parênteses em `CalculatorState`.

#### Scenario: Forma funcional recusada

- **WHEN** `evaluate("nCr(5,2)")` é chamado
- **THEN** o resultado é um erro com `code` igual a `"ERR-007"`

#### Scenario: Tecla produz a notação infixa

- **WHEN** o utilizador pressiona `5`, depois a tecla `nCr`, depois `2`
- **THEN** a expressão na linha de cálculo é `"5 nCr 2"` e SHALL NOT conter um abre-parênteses

#### Scenario: Ctrl na tecla nCr produz a permutação infixa

- **WHEN** o utilizador pressiona `5`, depois `Ctrl` e a tecla `nCr`, depois `2`
- **THEN** a expressão na linha de cálculo é `"5 nPr 2"`

#### Scenario: A vírgula permanece disponível

- **WHEN** o utilizador pressiona `Shift` e a tecla `.`
- **THEN** o token `,` é inserido, por continuar a ser necessário às conversões de coordenadas

### Requirement: Normalização independente da interface

Toda a normalização descrita nesta capacidade SHALL residir em `software/core/engine.py` e SHALL NOT importar nenhuma stack de UI (Tkinter, ttkbootstrap) nem depender de um front ativo, conforme a separação de camadas do PRD §8.

#### Scenario: Motor utilizável sem interface gráfica

- **WHEN** `software.core.engine` é importado num processo sem display e sem as dependências gráficas instaladas
- **THEN** a importação é bem-sucedida e todas as avaliações desta capacidade funcionam
