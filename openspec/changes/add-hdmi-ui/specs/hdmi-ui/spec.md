## ADDED Requirements

### Requirement: Front-end dedicado ao monitor HDMI
O sistema SHALL fornecer um front-end visual próprio para o monitor externo HDMI (`software/ui_hdmi/`), com layout projetado para tela maior (tipografia, área de histórico e alvo de foco/toque redimensionados), reutilizando o motor de cálculo de `software/core/` e o serviço de voz de `software/accessibility/speech.py` sem modificá-los.

#### Scenario: Inicialização no monitor
- **WHEN** o front-end HDMI é instanciado como saída ativa
- **THEN** ele exibe expressão e resultado usando `CalculatorState` de `software/core`, aciona `SpeechService` da mesma forma que o front do LCD (mesmas mensagens faladas, mesmo idioma pt-BR) e não importa nem duplica lógica de `software/core/engine.py`.

#### Scenario: Layout distinto do LCD, não escalado
- **WHEN** o front-end HDMI monta sua interface
- **THEN** ele usa dimensões, fontes e composição próprias (não uma cópia esticada de `ui_lcd/app.py`), aproveitando o espaço extra do monitor para mostrar mais histórico e/ou controles visíveis simultaneamente.

### Requirement: Paridade de acessibilidade entre fronts
Toda entrada e resultado anunciados pelo front-end HDMI SHALL seguir o mesmo catálogo de mensagens e prioridades de erro do PRD §13 usado pelo front do LCD (mesmo código → mesmo significado em UI e voz).

#### Scenario: Erro de domínio no monitor
- **WHEN** uma operação inválida ocorre com o front-end HDMI ativo (ex.: divisão por zero)
- **THEN** a UI do monitor exibe o mesmo código de erro (`ERR-0xx`/`WRN-0xx`) e o TTS anuncia o mesmo prefixo de prioridade ("Erro"/"Aviso") que o front do LCD anunciaria para o mesmo erro.

#### Scenario: Entrada exclusivamente por teclado físico
- **WHEN** o front-end HDMI está ativo
- **THEN** ele aceita entrada apenas do teclado físico mapeado por `software/hw_platform/keyboard.py` (RF-05), sem exigir mouse ou toque na tela para operação completa.
