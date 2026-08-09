## ADDED Requirements

### Requirement: Imagem bootável reprodutível gerada por script

O sistema SHALL fornecer, sob `system/rpi-os/alpine/`, o material de build que gera uma imagem de SO bootável para o Raspberry Pi 4B **executando apenas um script**, sem passos de configuração manual no aparelho. A imagem `.img` resultante MUST NOT ser versionada no Git — apenas os scripts, listas de pacotes e arquivos de configuração que a produzem.

#### Scenario: Build a partir do repositório produz a imagem

- **WHEN** um desenvolvedor executa o script de build documentado em `system/rpi-os/alpine/`
- **THEN** é gerado um arquivo de imagem gravável no cartão SD (ex.: `calculadora-alpine.img`) contendo o SO, o app e suas dependências, sem exigir edição manual dentro do Pi

#### Scenario: Nenhuma imagem binária é commitada

- **WHEN** o build termina e o repositório é inspecionado
- **THEN** nenhum arquivo `.img` (ou artefato binário equivalente da imagem) está sob controle de versão; apenas scripts e configuração de build estão versionados

### Requirement: Alvo Raspberry Pi 4B em aarch64

A imagem SHALL ter como alvo o Raspberry Pi 4B na arquitetura **aarch64 (64-bit)** e MUST arrancar nesse hardware a partir do cartão SD gravado.

#### Scenario: Gravação e arranque no Pi 4B

- **WHEN** a imagem gerada é gravada em um cartão SD e inserida em um Raspberry Pi 4B alimentado
- **THEN** o Pi completa o arranque a partir dela sem erro de arquitetura ou de firmware

### Requirement: Arranque direto na calculadora (kiosk)

Ao ser ligado, o dispositivo SHALL arrancar **direto na aplicação da calculadora** (`python3 -m software.app`), sem exibir desktop, gerenciador de janelas completo, tela de login interativa nem terminal. O ponteiro do mouse MUST permanecer oculto.

#### Scenario: Liga e mostra a calculadora

- **WHEN** o Raspberry Pi 4B é ligado com a imagem gravada
- **THEN** a interface da calculadora aparece na saída de vídeo ativa sem intervenção do usuário, e nenhum desktop, barra de tarefas ou prompt de login é apresentado

#### Scenario: Sem shell interativo exposto na tela

- **WHEN** o dispositivo termina o arranque em modo kiosk
- **THEN** não há terminal/console de login aguardando entrada visível ao usuário; a tela mostra apenas a aplicação

### Requirement: Ambiente gráfico mínimo para a UI Tkinter

A imagem SHALL prover um ambiente X11 mínimo (servidor X + inicialização via `xinit`/`.xinitrc`, sem desktop) suficiente para o front atual em `ttkbootstrap` (Tkinter) renderizar, ocupando a tela na saída HDMI ativa, com o LCD Waveshare 4,3" (800×480) como saída padrão.

#### Scenario: App renderiza no LCD ao arrancar

- **WHEN** o kiosk inicia com o LCD Waveshare 4,3" conectado como saída padrão
- **THEN** a janela da calculadora é desenhada ocupando a tela do LCD, legível na resolução 800×480

### Requirement: TTS offline em português embutido

A imagem SHALL incluir `espeak-ng` (e **não** o `espeak` clássico) e a cadeia de áudio necessária para que o `pyttsx3` sintetize voz em **português do Brasil** de forma **offline** (sem qualquer dependência de rede/nuvem), preservando o feedback por voz de entradas e resultados.

#### Scenario: Anúncio por voz sem rede

- **WHEN** o dispositivo está sem conexão de rede e o usuário realiza uma operação na calculadora
- **THEN** a entrada e/ou o resultado são anunciados por voz em português do Brasil, usando o motor local

#### Scenario: Motor de voz inicializa corretamente

- **WHEN** a aplicação inicia o serviço de TTS na imagem
- **THEN** a voz padrão inicializa via `espeak-ng` sem falhar (não ocorre o erro de `SetVoiceByName` observado com o `espeak` clássico)

### Requirement: Recuperação automática da aplicação

Se a aplicação da calculadora encerrar ou falhar, o sistema SHALL reiniciá-la automaticamente, sem exigir ação do usuário, mantendo o comportamento de appliance.

#### Scenario: App reinicia após queda

- **WHEN** o processo da calculadora termina inesperadamente durante o uso
- **THEN** a aplicação é reiniciada automaticamente e volta a exibir a interface, sem que o usuário precise reiniciar o dispositivo ou digitar comandos

### Requirement: Arranque enxuto (sem serviços de desktop)

Para favorecer o tempo de arranque (RNF-06), a imagem SHALL evitar serviços desnecessários ao appliance: MUST NOT incluir ambiente de desktop, gerenciador de login gráfico (display manager) ou serviços não essenciais habilitados por padrão.

#### Scenario: Somente serviços essenciais habilitados

- **WHEN** o conjunto de serviços habilitados no arranque da imagem é inspecionado
- **THEN** não há ambiente de desktop nem display manager habilitados; apenas os serviços necessários para autologin no console, vídeo (X mínimo), áudio e a aplicação estão ativos
