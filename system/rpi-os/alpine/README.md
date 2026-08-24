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
senão modo somente-áudio. A detecção ainda é **simulada** (`SimulatedHdmiPortReader`,
padrão `lcd_present=True`) — na prática a imagem sobe hoje sempre o **front do LCD**.
A detecção real de HDMI (RF-02/RF-09) continua em aberto.

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

