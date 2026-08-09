## Why

O PRD deixa a decisão de **SO e arranque** em aberto (§12) e trata o **boot rápido** como requisito de produto (**RNF-06**), mas hoje não existe uma forma reprodutível de gerar a imagem que roda no aparelho: o único empacotamento pronto é o `Dockerfile` Debian, útil só para desenvolvimento no PC (o próprio [docs/build-img-linux.md](../../../docs/build-img-linux.md) diz que Docker **não** é forma de embarcar a GUI no dispositivo final). Precisamos de uma imagem `.img` **enxuta, bootável e gerada por script** que faça o Raspberry Pi 4B ligar direto na calculadora, sem desktop nem terminal.

Escolhemos **Alpine Linux (aarch64)** como base minimalista: footprint pequeno e arranque curto (a favor do RNF-06), como alternativa mais leve e rápida de montar que o Buildroot, sem sair de um ecossistema com pacotes prontos (`python3`, `py3-tkinter`, `espeak-ng`, Xorg mínimo).

## What Changes

- **Nova via de empacotamento oficial do produto:** imagem **Alpine Linux aarch64** bootável para o cartão SD do Pi 4B, gerada 100% por script (sem configuração manual), que arranca em **modo kiosk** direto no app (`python3 -m software.app`) — sem desktop, sem login visível, sem cursor.
- **Ambiente gráfico mínimo (X11):** a imagem provê apenas o servidor X e o necessário para o Tkinter/`ttkbootstrap` desenhar a janela em tela cheia na saída HDMI ativa (LCD Waveshare 4,3" 800×480 por padrão).
- **Áudio TTS offline embutido:** `espeak-ng` (**não** o `espeak` clássico, incompatível com o `pyttsx3`) e a cadeia ALSA, atendendo ao feedback por voz contínuo (RF-04/RF-08) de forma offline (RNF-02).
- **Auto-restart do app:** se a calculadora fechar/cair, ela reinicia sozinha (papel de `Restart=always`), preservando a experiência de appliance.
- **Scripts versionados, imagem não:** todo o material de build (config do Alpine, lista de pacotes, `.xinitrc`/init do kiosk, `config.txt`/`usercfg.txt` do LCD) fica em `system/rpi-os/alpine/`; o `.img` gerado **não** é commitado (regra do [system/README.md](../../../system/README.md)).
- **Documentação:** registrar Alpine como terceira opção de SO/arranque em [docs/build-img-linux.md](../../../docs/build-img-linux.md), ao lado de Pi OS Lite e Buildroot.

## Capabilities

### New Capabilities

- `rpi-boot-image`: Geração reprodutível, a partir de scripts no repositório, de uma imagem de SO bootável para o Raspberry Pi 4B que faz o aparelho ligar direto na calculadora acessível (kiosk: X11 mínimo + app + TTS offline + auto-restart), sem desktop nem login interativo.

### Modified Capabilities

<!-- Nenhuma. openspec/specs/ está vazio: não há capability de spec existente cujos requisitos mudem. As referências ao PRD (RNF-06, §12, RF-01/RF-04/RNF-02) são a norma do produto, não specs OpenSpec. -->

## Impact

- **Novos artefatos** (sem tocar no código da aplicação): `system/rpi-os/alpine/` com script de build da imagem, lista de pacotes (apk), lançador do kiosk (`.xinitrc`/init), overrides de `config.txt`/`usercfg.txt` do LCD e um `README` de "como gerar e gravar".
- **Dependências de sistema na imagem:** `python3`, `python3-tkinter`, `espeak-ng`, `alsa-utils`/plugins, `xorg-server`/`xinit` mínimos, fontes; libs Python (`ttkbootstrap==1.20.4`, `pyttsx3==2.99`) instaladas via `pip` a partir de [software/requirements.txt](../../../software/requirements.txt).
- **Alvo de hardware:** Raspberry Pi 4B, arquitetura **aarch64** (64-bit); saída de vídeo padrão no LCD Waveshare 4,3" (HDMI). musl libc (Alpine) → validar Tkinter + `pyttsx3`/`espeak-ng` nesse ambiente é o principal risco técnico (detalhado no design).
- **Não afeta** `software/core/`, `ui_lcd/`, `accessibility/` nem os testes — a mudança é de empacotamento/arranque. O `Dockerfile` Debian de desenvolvimento permanece como está (coexistem).
- **CI/testes** de aplicação (Python 3.11) seguem inalterados; a validação da imagem é feita no hardware, fora do CI.

## Não-objetivos

- **Não** alterar o escopo matemático da calculadora (PRD §5) nem qualquer função do motor.
- **Não** acoplar o motor (`core/`) a nenhuma stack de UI; a imagem apenas executa `software/app.py` como já existe.
- **Não** implementar a detecção/troca automática HDMI↔LCD (RF-02/RF-09) nem a lógica de `DisplaySelector` (segue stub): a imagem desenha na saída X ativa; hotplug fica para trabalho à parte.
- **Não** integrar drivers de teclado GPIO nem leitura do UPS HAT (I2C) como parte desta imagem — usa o que já existir em `hw_platform/`.
- **Não** substituir o `Dockerfile` Debian de desenvolvimento nem propor Docker como forma de embarcar no aparelho final.
- **Não** commitar arquivos `.img` no Git; entregar apenas os scripts que os geram.
- **Não** fixar meta numérica de tempo de boot (RNF-06) nesta change — a meta é medida no hardware depois.
