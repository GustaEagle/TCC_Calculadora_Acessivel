# Imagem Alpine (aarch64) — kiosk da calculadora no Raspberry Pi 4B

Gera uma imagem **Alpine Linux 3.24.1 (aarch64)** bootável que faz o Raspberry
Pi 4B **arrancar direto na calculadora** (modo kiosk): sem desktop, sem login
visível, sem cursor. É a via de empacotamento do **produto final** — enxuta e
gerada por script — alternativa mais leve ao Buildroot descrito em
[../../../docs/build-img-linux.md](../../../docs/build-img-linux.md).

> A aplicação (`software/`) **não** é alterada; aqui só a empacotamos e
> configuramos o arranque. Ver o plano em
> `openspec/changes/add-alpine-rpi-image/` (proposal / design / specs / tasks).

## Conteúdo desta pasta

| Arquivo | Papel |
| ------- | ----- |
| `build-alpine-img.sh` | Monta o rootfs Alpine (chroot qemu), instala pacotes/pip, configura o kiosk e empacota o `.img`. |
| `packages` | Lista de pacotes `apk` instalados na imagem (um por linha). |
| `overlay/` | Arquivos copiados para o rootfs: `.profile`/`.xinitrc` do kiosk, `etc/asound.conf`, `boot/usercfg.txt`. |
| `.work/` | Diretório de trabalho do build (rootfs/downloads/mount). **Ignorado pelo git.** |

O `.img` gerado e o `.work/` **nunca** são versionados (regra do
[../README.md](../README.md); ver `.gitignore`).

## Como a imagem arranca (kiosk)

```
Liga o Pi (aarch64)
  → firmware + kernel linux-rpi (config.txt / cmdline.txt)
  → autologin do usuário "kiosk" no tty1 (agetty, via /etc/inittab)
  → ~/.profile dispara: startx
  → ~/.xinitrc: xset s off -dpms; unclutter; e o laço
        while true; do python3 -m software.app; done   (auto-restart)
  → só a janela da calculadora na tela
```

## Pré-requisitos (máquina de build Linux x86_64)

Build **cross** no PC via `qemu-user`/binfmt (não precisa de um Pi para montar):

```bash
sudo apt install -y qemu-user-static binfmt-support parted dosfstools e2fsprogs curl
# Se o chroot aarch64 não executar, registre o binfmt:
sudo update-binfmts --enable qemu-aarch64
# (alternativa: docker run --privileged --rm tonistiigi/binfmt --install arm64)
```

## Gerar a imagem

```bash
cd system/rpi-os/alpine
sudo ./build-alpine-img.sh
```

Saída: `calculadora-alpine-3.24.1-aarch64.img` nesta pasta. O script:

1. baixa e **verifica o sha256** do minirootfs oficial;
2. instala os pacotes (`packages`) + kernel/firmware do Pi + as libs Python
   fixadas em [../../../software/requirements.txt](../../../software/requirements.txt);
3. configura autologin/kiosk e copia `software/` para `/opt/calculadora/`;
4. roda smokes no chroot (`import tkinter`/`ttkbootstrap` é **gate**; `pyttsx3.init()`
   é aviso — áudio real só no hardware);
5. empacota a imagem (boot FAT32 + root ext4 gravável).

### Rebuild rápido ao mudar o código do app

`CONTINUE=1` (ou `REUSE_ROOTFS=1`) reaproveita os **pacotes** já instalados em
`.work/rootfs` — pula download/apk/pip, a fase lenta — mas **recopia `software/`
e o overlay**, então a imagem sai sempre com o código atual do repositório:

```bash
make rpi-img-continue        # a partir da raiz do repo
```

Requer que `.work/` exista (de um build anterior). Se foi apagado, o build é
completo de novo.

### Qual front sobe no kiosk

O kiosk roda `python3 -m software.app`, que escolhe a saída sozinho
(`hw_platform/display.py`, PRD §7): monitor externo tem prioridade, senão o LCD,
senão modo somente-áudio.

A detecção lê o estado real das portas em `/sys/class/drm` (`SysfsHdmiPortReader`),
usando a cablagem fixada no PRD §6: **HDMI0 = LCD**, **HDMI1 = monitor externo**.
Fora do Pi (PC de desenvolvimento, CI) não há esses conectores e o código cai
sozinho no `SimulatedHdmiPortReader`.

**Confirmar no primeiro boot** quais nomes de conector o kernel dá a cada porta —
o padrão assumido é `HDMI-A-1` para o HDMI0 e `HDMI-A-2` para o HDMI1, mas isso
varia com kernel/driver (PRD §11):

```sh
cd /opt/calculadora && python3 -m software.app --list-outputs
```

Se os nomes forem outros, não é preciso mexer no código: defina as variáveis
`CALC_LCD_CONNECTOR` e `CALC_MONITOR_CONNECTOR` em `overlay/home/kiosk/.xinitrc`.

### Dois HDMI ligados ao mesmo tempo

O PRD §7.2 é explícito: com o monitor externo reconhecido, a interface aparece
**apenas** nele e o LCD **não** mostra a mesma interface principal. Sem ajuda,
não é isso que acontece.

**Por que o X estende por omissão.** Com as duas portas conectadas no boot, o
driver `modesetting` autoconfigura os dois CRTCs lado a lado — um único desktop
estendido cobrindo as duas telas. Isso é decidido pelo servidor X **antes** de o
Python arrancar, então nenhuma lógica dentro do app chega a tempo de impedir que
apareça. Pior: como o kiosk não tem gerenciador de janelas, o X coloca a janela
em (0,0), que nesse framebuffer combinado é o canto do **LCD**, não do monitor.

**Como o `--apply-video-layout` corrige.** A sessão gráfica
(`overlay/home/kiosk/.xinitrc`) chama, logo depois dos `xset` e **antes** do laço
do app:

```sh
python3 -m software.app --apply-video-layout
```

Esse modo consulta o `DisplaySelector` (a mesma regra do §7, sem duplicá-la em
shell), aplica por `xrandr` o layout exclusivo — a saída escolhida ligada e
primária, a outra desligada — e encerra **sem abrir nenhuma janela**. Quando o
app sobe logo a seguir, o framebuffer já é o de um painel só.

Três detalhes que fazem a diferença entre isto funcionar e falhar em silêncio:

- **Os nomes de saída são descobertos, não adivinhados.** A versão anterior
  convertia `HDMI-A-2` → `HDMI-2` por convenção; num kernel que use outra grafia
  o `xrandr` falhava, o layout estendido permanecia e ninguém via o erro. Agora a
  ordem é: variável de ambiente → saída realmente presente em `xrandr --query` →
  convenção. A comparação ignora hífens e maiúsculas, então `HDMI-A-2`, `HDMI-2`,
  `HDMI2` e `hdmi-2` são reconhecidos como a mesma porta.
- **O resultado é verificado.** O código de saída do `xrandr` diz que o comando
  foi aceite, não que o CRTC mudou. Depois de aplicar, o estado é relido e só
  então se reporta sucesso. Divergência vira **WRN-012** no log.
- **É idempotente.** Se o layout já está correto, o `xrandr` não é chamado — é o
  que evita um flash de reconfiguração a cada arranque, já que o app reaplica o
  layout por dentro a cada troca de front.

O `usercfg.txt` **não** muda: `max_framebuffers=2` tem de ficar, porque é ele que
dá framebuffer à segunda porta e, com `vc4-kms-v3d`, o hotplug de que o RF-09
depende. A exclusividade resolve-se no X, não castrando o firmware.

**Diagnóstico.** O `--list-outputs` mostra numa só execução os conectores DRM, as
saídas do `xrandr` com o seu estado, e o mapeamento efetivo de cada papel:

```sh
cd /opt/calculadora && python3 -m software.app --list-outputs
```

E o que o layout fez fica registado em `~/calculadora.log` (sobreponível por
`CALC_LOG_FILE`) — no kiosk o tty1 fica coberto pelo X, então o ficheiro é a
única forma de distinguir um `xrandr` que funcionou de um que falhou.

### Monitor ligado com a calculadora já em uso (RF-09)

Este é o fluxo normal, não uma exceção: o LCD é interno e está sempre presente no
boot, então o **monitor externo é sempre ligado depois**.

A troca acontece **dentro do mesmo processo**, sem reiniciar o app nem o X:

1. `DisplayWatcher` relê as portas a cada 2 s (`/sys/class/drm`).
2. Ao detectar mudança, o front anuncia o **WRN-012** («Aviso 012. Saída de vídeo
   alterada.») e fecha só a sua janela.
3. O entrypoint chama o `xrandr` para ligar o painel novo e desligar o antigo.
4. Constrói o outro front **em volta do mesmo `CalculatorState`**.

Como o estado é o mesmo objeto, **a conta em andamento, o histórico e o modo
angular sobrevivem à troca** — quem estava digitando continua de onde parou, em
outra tela. A fala também não é cortada: o `SpeechService` não é derrubado.

Os nomes de saída do `xrandr` não são os mesmos do sysfs: `HDMI-A-1` (sysfs) vira
`HDMI-1` (driver `modesetting`). Se este kernel usar outra convenção, corrija com
`CALC_LCD_XRANDR_OUTPUT` / `CALC_MONITOR_XRANDR_OUTPUT` no `.xinitrc`:

```sh
xrandr --listmonitors   # nomes que o X reconhece
```

Se o painel novo aparecer cortado ou numa resolução errada, é a geometria máxima
do servidor X: acrescente um `Virtual` grande o bastante para os dois painéis em
`/etc/X11/xorg.conf.d/10-virtual.conf`. Com `modesetting`/KMS o padrão normalmente
já é suficiente, por isso não vai um `xorg.conf` na imagem — um arquivo errado aí
deixa o aparelho sem UI nenhuma.

**Isto depende do kernel atualizar o status do conector em tempo de execução.** Com
`dtoverlay=vc4-kms-v3d` (o que está no `usercfg.txt`) o driver DRM faz isso; no
caminho legado/firmware o modo é fixado no boot e **nenhum código em espaço de
usuário** consegue ver um monitor que chegou depois. Confirme no hardware:

```sh
# Sem o monitor ligado:
cat /sys/class/drm/card*-HDMI-A-2/status     # esperado: disconnected
# Ligue o monitor no HDMI1, espere ~5 s, repita:
cat /sys/class/drm/card*-HDMI-A-2/status     # tem de virar: connected
```

Se o valor **não mudar** sem reiniciar, o hotplug não chega ao kernel e as opções são:

- Manter `vc4-kms-v3d` e investigar (é o caminho que suporta hotplug); ou
- Aceitar a limitação: o monitor tem de estar ligado **no boot**, e trocar de tela
  exige reiniciar a calculadora. Nesse caso o watcher fica inerte, sem prejuízo.
- **Não** use `hdmi_force_hotplug` para "resolver": ele força a porta a reportar-se
  sempre como conectada, o que faz o app achar que o monitor está sempre lá e nunca
  usar o LCD.

### Fallback: build nativo no próprio Pi

Se o cross-build (qemu/binfmt) der problema, dá para rodar os mesmos passos
**dentro de um Raspberry Pi** já com Alpine/Pi OS: como já é aarch64, dispensa o
`qemu-aarch64-static` e o binfmt (o chroot roda nativo). Útil como plano B.

## Gravar no cartão

```bash
# ATENÇÃO: /dev/sdX é o SEU cartão — confira com lsblk; o comando apaga o alvo.
sudo dd if=calculadora-alpine-3.24.1-aarch64.img of=/dev/sdX bs=4M conv=fsync status=progress
```

(Ou use o Raspberry Pi Imager → "Use custom".) Opcional: encolher com `pishrink`.

## Checklist de validação no hardware (Raspberry Pi 4B)

Estes passos **só** podem ser confirmados no aparelho (marcados no build com
`# VALIDAR NO HARDWARE`):

- [ ] Liga e sobe **direto na calculadora** (sem desktop/login/cursor).
- [ ] UI `ttkbootstrap` em **tela cheia** e legível no LCD Waveshare 4,3" (800×480).
- [ ] **TTS pt-BR** anuncia entradas/resultados **sem rede** (offline).
- [ ] Matar o app (`pkill -f software.app`) → ele **reinicia sozinho**.
- [ ] Medir o **tempo de arranque** até a UI (referência do RNF-06).
- [ ] `--list-outputs` confirma que **HDMI0 (LCD)** e **HDMI1 (monitor)** correspondem
      a `HDMI-A-1` e `HDMI-A-2` — se não, ajustar as variáveis no `.xinitrc`.
- [ ] Ligar um **monitor externo no HDMI1** com a calculadora **já ligada** → a voz
      anuncia o **WRN-012** e a UI aparece no monitor **sem reiniciar** (a expressão
      digitada continua lá). Remover o monitor → volta para o LCD do mesmo jeito.
- [ ] **Duas portas ligadas no boot** (LCD + monitor) → **só o monitor** acende; o
      LCD fica **apagado**, sem mostrar área de trabalho nenhuma, e em nenhum
      instante do arranque aparece um desktop estendido nas duas telas (PRD §7.2).
- [ ] Registar aqui no README os **nomes reais** devolvidos por `xrandr --query`
      (e não `--listmonitors`, que só lista as saídas **ativas** e por isso nunca
      mostraria o painel que se quer ligar):

      | Papel            | Conector DRM | Saída `xrandr` |
      | ---------------- | ------------ | -------------- |
      | LCD (HDMI0)      | _a preencher_ | _a preencher_ |
      | Monitor (HDMI1)  | _a preencher_ | _a preencher_ |

- [ ] Conferir em `~/calculadora.log` que o layout foi **aplicado e verificado**
      (linha `layout de video aplicado e verificado: modo=... alvo=...`). Se
      aparecer **WRN-012**, o log traz o modo pretendido e os nomes tentados —
      compare-os com a tabela acima e, se divergirem, defina
      `CALC_LCD_XRANDR_OUTPUT` / `CALC_MONITOR_XRANDR_OUTPUT` no `.xinitrc`.
- [ ] **Interruptor físico** do LCD desligado, sem monitor → `--list-outputs` mostra o
      LCD como `disconnected` e o app cai em **somente-áudio** (RF-04). Se continuar
      `connected`, o interruptor não corta o hotplug detect e a detecção do
      interruptor precisará de um GPIO próprio (ver `display.py`).

### Ajustes prováveis na 1ª vez

- **Vídeo do LCD:** começar por `dtoverlay=vc4-kms-v3d` (em `overlay/boot/usercfg.txt`);
  se o painel não sincronizar, usar o bloco `hdmi_cvt 800 480` comentado lá
  (ver [../../../docs/waveshare/README.md](../../../docs/waveshare/README.md)).
- **Áudio:** conferir `aplay -l` e ajustar `card` em `overlay/etc/asound.conf`
  (HDMI vs. jack 3,5 mm).
- **dtb/overlays:** o layout exato do `linux-rpi`/`raspberrypi-bootloader` pode
  variar por versão — se não bootar, checar se `bcm2711-rpi-4-b.dtb` e `overlays/`
  foram para a raiz da partição de boot.

### RODAR BUILD
  cd "/home/usuario/Área de trabalho/TCC_Calculadora_Acessivel/system/rpi-os/alpine"
  sudo ./build-alpine-img.sh 2>&1 | tee build.log

