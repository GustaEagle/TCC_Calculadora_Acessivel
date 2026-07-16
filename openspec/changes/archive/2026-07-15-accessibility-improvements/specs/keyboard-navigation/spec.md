## ADDED Requirements

### Requirement: Operação completa por teclado

Todas as funções da calculadora SHALL ser acessíveis por teclado, sem depender do mouse, cobrindo entrada de dígitos, operadores, funções, avaliação, limpeza e apagar.

#### Scenario: Entrada e avaliação por teclado
- **WHEN** o usuário digita uma expressão e aciona a avaliação pelo teclado
- **THEN** a expressão é montada e avaliada sem uso do mouse

#### Scenario: Limpar e apagar por teclado
- **WHEN** o usuário aciona as teclas de limpar e apagar
- **THEN** as ações correspondentes (AC e DEL) são executadas

### Requirement: Navegação por foco entre elementos

A interface SHALL permitir navegar entre elementos interativos por teclado (ex.: Tab/setas), com o foco visível e anunciável, em ordem previsível.

#### Scenario: Ordem de foco previsível
- **WHEN** o usuário navega com a tecla de foco
- **THEN** o foco percorre os elementos em ordem lógica e previsível
- **AND** o elemento focado é identificável visual e/ou sonoramente

### Requirement: Atalhos adicionais avaliados e documentados

Os atalhos de teclado disponíveis SHALL ser documentados, e a necessidade de atalhos adicionais (para funções científicas e ações frequentes) SHALL ser avaliada e, quando adotada, refletida no mapeamento de teclas.

#### Scenario: Atalhos documentados
- **WHEN** um atalho de teclado existe
- **THEN** ele está documentado no mapeamento de teclas do produto
