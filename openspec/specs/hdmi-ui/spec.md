# hdmi-ui Specification

## Purpose
TBD - created by archiving change add-hdmi-ui. Update Purpose after archive.

## Requirements

### Requirement: Front-end dedicado ao monitor HDMI
O sistema SHALL fornecer um front-end visual próprio para o monitor externo HDMI (`software/ui_hdmi/`), com layout projetado para tela maior (tipografia, área de histórico e alvo de foco/toque redimensionados), reutilizando o motor de cálculo de `software/core/` e o serviço de voz de `software/accessibility/speech.py` sem modificá-los.

#### Scenario: Inicialização no monitor
- **WHEN** o front-end HDMI é instanciado como saída ativa
- **THEN** ele exibe expressão e resultado usando `CalculatorState` de `software/core`, aciona `SpeechService` da mesma forma que o front do LCD (mesmas mensagens faladas, mesmo idioma pt-BR) e não importa nem duplica lógica de `software/core/engine.py`.

#### Scenario: Layout distinto do LCD, não escalado
- **WHEN** o front-end HDMI monta sua interface
- **THEN** ele usa dimensões, fontes e composição próprias (não uma cópia esticada de `ui_lcd/app.py`), aproveitando o espaço extra do monitor para mostrar mais histórico e/ou controles visíveis simultaneamente.

### Requirement: Layout responsivo à resolução do monitor
O front-end HDMI SHALL adaptar seu layout (dimensionamento de expressão, resultado, teclado e histórico) à resolução real reportada pelo sistema na inicialização, em vez de assumir uma resolução-alvo fixa.

#### Scenario: Monitor com resolução diferente do padrão
- **WHEN** o front-end HDMI é iniciado em um monitor com resolução diferente de outros já testados (ex.: 1366x768 em vez de 1920x1080)
- **THEN** os elementos da interface se realocam proporcionalmente ao espaço disponível (sem cortar, sobrepor ou deixar áreas vazias fixas desproporcionais), sem exigir alteração de código para essa resolução.

#### Scenario: Redimensionamento manual da janela
- **WHEN** a janela do front-end HDMI é redimensionada manualmente (ex.: durante testes locais no PC)
- **THEN** o layout recalcula proporções via grid/weight, mantendo a legibilidade e a proporção relativa entre expressão, resultado, teclado e histórico.

### Requirement: Paridade de acessibilidade entre fronts
Toda entrada e resultado anunciados pelo front-end HDMI SHALL seguir o mesmo catálogo de mensagens e prioridades de erro do PRD §13 usado pelo front do LCD (mesmo código → mesmo significado em UI e voz).

#### Scenario: Erro de domínio no monitor
- **WHEN** uma operação inválida ocorre com o front-end HDMI ativo (ex.: divisão por zero)
- **THEN** a UI do monitor exibe o mesmo código de erro (`ERR-0xx`/`WRN-0xx`) e o TTS anuncia o mesmo prefixo de prioridade ("Erro"/"Aviso") que o front do LCD anunciaria para o mesmo erro.

#### Scenario: Entrada exclusivamente por teclado físico
- **WHEN** o front-end HDMI está ativo
- **THEN** ele aceita entrada apenas do teclado físico mapeado por `software/hw_platform/keyboard.py` (RF-05), sem exigir mouse ou toque na tela para operação completa.
