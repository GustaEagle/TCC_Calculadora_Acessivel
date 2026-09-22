# display-switching Specification

## Purpose
TBD - created by archiving change add-hdmi-ui. Update Purpose after archive.

## Requirements

### Requirement: Prioridade do monitor HDMI sobre o LCD
Quando as saídas HDMI do LCD e do monitor externo estiverem ambas reconhecidas, o sistema SHALL selecionar o front-end do monitor (`DisplayMode.HDMI`) como saída principal, e o LCD SHALL NOT exibir a mesma interface principal.

#### Scenario: LCD e monitor reconhecidos simultaneamente
- **WHEN** `DisplaySelector.current_mode()` é consultado e tanto a saída HDMI do LCD quanto a do monitor externo estão reconhecidas
- **THEN** o resultado é `DisplayMode.HDMI`

### Requirement: Uso do LCD quando o monitor não está presente
Quando apenas a saída HDMI do LCD estiver reconhecida (monitor externo ausente), o sistema SHALL selecionar o front-end do LCD (`DisplayMode.LCD`).

#### Scenario: Somente LCD reconhecido
- **WHEN** `DisplaySelector.current_mode()` é consultado, a saída HDMI do LCD está reconhecida e a do monitor externo não está
- **THEN** o resultado é `DisplayMode.LCD`

### Requirement: Modo somente áudio sem vídeo utilizável
Quando nenhuma saída de vídeo estiver utilizável (nem LCD nem monitor reconhecidos, incluindo o caso do interruptor físico do LCD cortando sua saída HDMI), o sistema SHALL selecionar `DisplayMode.AUDIO_ONLY`, mantendo entrada por teclado e feedback por voz funcionando (RF-04).

#### Scenario: Nenhuma saída de vídeo reconhecida
- **WHEN** `DisplaySelector.current_mode()` é consultado e nem a saída HDMI do LCD nem a do monitor externo estão reconhecidas
- **THEN** o resultado é `DisplayMode.AUDIO_ONLY`

#### Scenario: Interruptor físico do LCD desligado sem monitor presente
- **WHEN** o interruptor físico do LCD corta sua saída HDMI (painel em standby) e o monitor externo não está reconhecido
- **THEN** `DisplaySelector.current_mode()` retorna `DisplayMode.AUDIO_ONLY`, tratando a saída do LCD como indisponível

### Requirement: Ponto de entrada único desperta o front correto
O sistema SHALL fornecer um único ponto de entrada que consulta `DisplaySelector.current_mode()` na inicialização e instancia exclusivamente o front correspondente (`ui_hdmi` para `HDMI`, `ui_lcd` para `LCD`, ou um laço somente-áudio para `AUDIO_ONLY`), sem instanciar mais de um front visual ao mesmo tempo.

#### Scenario: Inicialização com monitor presente
- **WHEN** o ponto de entrada é executado e `DisplaySelector.current_mode()` retorna `DisplayMode.HDMI`
- **THEN** apenas o front-end `ui_hdmi` é instanciado; `ui_lcd` não é iniciado

#### Scenario: Inicialização sem vídeo utilizável
- **WHEN** o ponto de entrada é executado e `DisplaySelector.current_mode()` retorna `DisplayMode.AUDIO_ONLY`
- **THEN** nenhum front visual (`ui_lcd` ou `ui_hdmi`) é instanciado, e o sistema opera aceitando teclado e respondendo por `SpeechService`
