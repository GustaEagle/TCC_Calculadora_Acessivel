## Why

O `software/ui_hdmi/` ainda está vazio (só `.gitkeep`); hoje existe apenas o front do LCD 4,3" (`ui_lcd/`). Sem a UI do monitor HDMI, RF-02/RF-03 do PRD (alternar para o monitor externo como saída preferencial) não podem ser cumpridos, e `DisplaySelector` (hw_platform/display.py) é um stub que sempre retorna `LCD`.

## What Changes

- Criar o front-end `ui_hdmi/` (ttkbootstrap), reaproveitando `core/` (motor de cálculo) e `accessibility/speech.py` sem alterações, com layout redesenhado para uma área maior (tipografia e alvo de toque/foco maiores, mais espaço para histórico) em vez de simplesmente escalar o layout do LCD.
- Implementar a lógica real de `DisplaySelector` (hoje stub) para detectar as duas saídas HDMI do Raspberry Pi e aplicar a prioridade do PRD §7: monitor presente → só monitor (`DisplayMode.HDMI`); só LCD presente → só LCD (`DisplayMode.LCD`); nenhum → `DisplayMode.AUDIO_ONLY`.
- Criar um ponto de entrada comum (`software/app.py` ou equivalente) que escolhe entre `ui_lcd.CalculatorApp` e o novo `ui_hdmi.CalculatorApp` a partir do `DisplaySelector`, em vez de cada front assumir sozinho que é o ativo.
- Cobrir a lógica de seleção de saída com testes (`software/tests/`) para as três combinações da seção 7.4 do PRD (LCD só, monitor só/preferencial, nenhum vídeo).

## Capabilities

### New Capabilities
- `hdmi-ui`: front-end visual para o monitor externo via HDMI, com layout próprio para tela maior, reutilizando o motor de cálculo e o TTS já existentes.
- `display-switching`: seleção da saída visual ativa (LCD vs. monitor HDMI vs. somente áudio) segundo a prioridade e o fluxo lógico do PRD §7, incluindo o ponto de entrada que decide qual front instanciar.

### Modified Capabilities
(nenhuma — ainda não há specs existentes em `openspec/specs/`)

## Impact

- Código novo: `software/ui_hdmi/*.py` (app.py, palette/formatting/error_messages equivalentes aos do LCD onde fizer sentido reaproveitar).
- Código alterado: `software/hw_platform/display.py` (`DisplaySelector` deixa de ser stub); possível novo `software/app.py` como entrypoint único.
- Sem alterações em `software/core/` (motor de cálculo permanece agnóstico de UI, conforme regra do projeto) nem no catálogo de erros do PRD §13.
- Testes novos em `software/tests/` para `DisplaySelector`.
- Fora do escopo (não-objetivos): detecção real de hardware GPIO/HDMI em produção (fica simulável/mockável como os demais adaptadores de `hw_platform/`), qualquer alteração ao catálogo de funções matemáticas (§5) ou aos códigos de erro (§13), e o desenho físico do interruptor do LCD (hardware).
