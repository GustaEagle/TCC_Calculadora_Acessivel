## MODIFIED Requirements

### Requirement: Paridade de acessibilidade entre fronts
Toda entrada e resultado anunciados pelo front-end HDMI SHALL seguir o mesmo catálogo de mensagens e prioridades de erro do PRD §13 usado pelo front do LCD (mesmo código → mesmo significado em UI e voz).

#### Scenario: Erro de domínio no monitor
- **WHEN** uma operação inválida ocorre com o front-end HDMI ativo (ex.: divisão por zero)
- **THEN** a UI do monitor exibe o mesmo código de erro (`ERR-0xx`/`WRN-0xx`) e o TTS anuncia o mesmo prefixo de prioridade ("Erro"/"Aviso") que o front do LCD anunciaria para o mesmo erro.

#### Scenario: Entrada exclusivamente por teclado físico
- **WHEN** o front-end HDMI está ativo
- **THEN** ele aceita entrada do teclado físico do produto, a matriz 6x7 lida por GPIO (capacidade `keypad-matrix`), pelo mesmo tratamento de tokens do front do LCD, sem exigir mouse ou toque na tela para operação completa (RF-05); o teclado de PC mapeado por `software/hw_platform/keyboard.py` continua aceito como meio de desenvolvimento e testes.
