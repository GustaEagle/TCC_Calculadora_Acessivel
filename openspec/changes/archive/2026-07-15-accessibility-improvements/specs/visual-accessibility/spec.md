## ADDED Requirements

### Requirement: Contraste mínimo verificável

Os elementos visuais (texto sobre botões, expressão, resultado e mensagens) SHALL atender a um contraste mínimo verificável alinhado ao RF-12, adotando como critério a razão de contraste **WCAG 2.1 AA** (≥ 4,5:1 para texto normal; ≥ 3:1 para texto grande).

#### Scenario: Texto de botão atende ao contraste
- **WHEN** um botão é renderizado com sua cor de fundo e cor de texto
- **THEN** a razão de contraste entre texto e fundo é de pelo menos 4,5:1 (ou 3:1 para tipografia grande)

#### Scenario: Display atende ao contraste
- **WHEN** a expressão e o resultado são exibidos
- **THEN** o contraste do texto sobre o fundo do display atende ao critério WCAG AA

### Requirement: Paleta coerente por categoria

A paleta SHALL diferenciar categorias de botões (numéricos, operadores, funções científicas, controle) de forma consistente e com contraste adequado, sem depender apenas da cor para transmitir significado.

#### Scenario: Categorias distinguíveis além da cor
- **WHEN** o usuário observa o teclado
- **THEN** categorias de botões são distinguíveis por mais de um atributo (ex.: cor + posição/rótulo), não só matiz

### Requirement: Legibilidade de tipografia

O tamanho e o peso da tipografia SHALL ser adequados para baixa visão no painel de 800x480 e no monitor externo, mantendo a expressão e o resultado legíveis.

#### Scenario: Resultado permanece legível ao truncar
- **WHEN** a expressão ou o resultado excede a largura disponível
- **THEN** o conteúdo é truncado preservando a parte mais relevante e sem reduzir a tipografia abaixo do mínimo legível
