## ADDED Requirements

### Requirement: Exibição em notação convencional

A interface SHALL exibir a expressão em edição usando **notação matemática convencional**, enquanto o motor de cálculo continua recebendo os tokens canônicos internos. A camada de exibição MUST NOT alterar o valor enviado ao `CalculationEngine`.

#### Scenario: Raiz quadrada exibida com símbolo
- **WHEN** o usuário insere a função de raiz quadrada
- **THEN** a expressão exibida mostra `√(` em vez de `sqrt(`
- **AND** o motor recebe o token `sqrt(` ao avaliar

#### Scenario: Constantes e inverso exibidos com símbolo
- **WHEN** o usuário insere pi ou o inverso de um valor
- **THEN** a expressão exibida mostra `π` e `x⁻¹` respectivamente
- **AND** o resultado numérico é idêntico ao da notação interna

#### Scenario: Funções exibidas sem parêntese interno cru
- **WHEN** o usuário insere funções como seno, log ou logaritmo em base
- **THEN** a expressão exibida usa rótulos legíveis (ex.: `sen(`, `log(`, `log_b(`) coerentes com os botões
- **AND** a avaliação produz o mesmo resultado da expressão canônica

### Requirement: Consistência entre rótulo, exibição e voz

O rótulo do botão, o texto exibido na expressão e o nome falado pelo TTS SHALL referir-se à mesma operação de forma coerente, sem divergência de nomenclatura para o mesmo símbolo.

#### Scenario: Mesma operação, mesma nomenclatura
- **WHEN** um símbolo é inserido por botão ou teclado
- **THEN** o rótulo visual, o trecho na expressão e o anúncio por voz descrevem a mesma operação sem contradição
