## 1. Estrutura e versionamento

- [x] 1.1 Criar `system/rpi-os/alpine/` com subpastas `overlay/` (arquivos que vão para o rootfs) e `README.md` (esqueleto).
- [x] 1.2 Adicionar/confirmar no `.gitignore` a exclusão de artefatos de imagem (`*.img`, `*.img.gz`, diretórios de work/mount do build) sob `system/rpi-os/alpine/`.
- [x] 1.3 Criar `system/rpi-os/alpine/packages` com a lista de pacotes `apk` (um por linha) e um comentário com a **versão do Alpine fixada** (3.24.1 aarch64).

## 2. Base e dependências (decisões D1, D5, D6, D7)

- [x] 2.1 Fixar a versão do Alpine e a URL/checksum do **minirootfs** `alpine-minirootfs-3.24.1-aarch64` no script de build (verificação de hash obrigatória); kernel/firmware do Pi vêm por `apk` (`linux-rpi`, `raspberrypi-bootloader`).
- [x] 2.2 Preencher `packages` com: `python3 python3-tkinter`, `espeak-ng`, `alsa-lib alsa-utils alsa-plugins`, `xorg-server xinit xset`, driver de vídeo (`mesa-dri-gallium` p/ vc4-kms + `xf86-video-fbdev` de reserva), `libinput/eudev`, `unclutter-xfixes`, `font-dejavu`, `py3-pip`.
- [x] 2.3 Registrar as libs Python via `pip` a partir de [software/requirements.txt](../../../software/requirements.txt) (`ttkbootstrap==1.20.4`, `pyttsx3==2.99`), com `--break-system-packages`.

## 3. Script de build da imagem (decisão D2)

- [x] 3.1 Escrever `system/rpi-os/alpine/build-alpine-img.sh` que baixa+verifica o **minirootfs**, monta o **rootfs ext4 "sys"** (D1) e prepara a **partição FAT de boot** (kernel `vmlinuz-rpi`/initramfs/dtbs obtidos via `apk`).
- [x] 3.2 Montar o rootfs aarch64 em **chroot com `qemu-aarch64-static`/binfmt** e executar `apk add` (lista do passo 2.2) + `pip install` (passo 2.3) — tudo baked, **sem** instalação por rede no primeiro boot.
- [x] 3.3 Empacotar as duas partições num `.img` (loopback: `parted`+`mkfs`+`mount`+`cp`); a imagem final não é versionada.
- [x] 3.4 Documentar no script/README o **fallback de build nativo no Pi** (Alternativa A do D2) para o caso de o cross/binfmt falhar.

## 4. Boot e vídeo do Pi 4B (decisão D3)

- [x] 4.1 Gerar `usercfg.txt`/`config.txt` na partição de boot com o modo do **LCD Waveshare 4,3" B** (seguir [docs/waveshare/README.md](../../../docs/waveshare/README.md)), `disable_overscan` e `dtoverlay=vc4-kms-v3d` (com fbdev/`hdmi_cvt` como plano B).
- [x] 4.2 Ajustar `cmdline.txt`: `root=` para a partição ext4 (`mmcblk0p2`), `console=tty1` e arranque silencioso (quiet), sem prompt visível.

## 5. Kiosk: autologin + X + auto-restart (decisão D4)

- [x] 5.1 Criar usuário `kiosk` no rootfs e configurar autologin no `tty1` via `/etc/inittab` (`agetty --autologin kiosk`), sem getty de login visível.
- [x] 5.2 Adicionar `overlay/home/kiosk/.profile` que dispara `startx` apenas no `tty1`.
- [x] 5.3 Adicionar `overlay/home/kiosk/.xinitrc` com `xset s off -dpms`, ocultação de cursor (`unclutter`) e o laço `while true; do python3 -m software.app; done` (auto-restart) a partir de `/opt/calculadora`.
- [x] 5.4 Garantir que nenhum desktop/display manager é instalado ou habilitado (requisito "arranque enxuto").

## 6. Áudio e TTS offline (decisões D6, D7)

- [x] 6.1 Adicionar `overlay/etc/asound.conf` selecionando a saída de áudio do Pi (HDMI **ou** jack — documentado, ajuste por `aplay -l` no hardware).
- [x] 6.2 Se o `pyttsx3` procurar `libespeak.so.1`, criar symlink de compatibilidade para `libespeak-ng.so.1` no rootfs (feito no script, defensivo).
- [x] 6.3 Confirmar/fixar a voz **pt-BR** usada pelo `speech.py` no ambiente `espeak-ng` do Alpine.

## 7. Baking do app no rootfs (decisão D8)

- [x] 7.1 Copiar `software/` para `/opt/calculadora/software/` no rootfs (sem `.venv`, `__pycache__`).
- [x] 7.2 Definir o working dir de execução em `/opt/calculadora` para que `python3 -m software.app` resolva o pacote `software`.

## 8. Validação automática no build (chroot) — executa ao rodar o script

- [x] 8.1 No chroot, rodar smoke de GUI: `python3 -c "import tkinter, ttkbootstrap"` sem erro (import de `_tkinter` em musl) — **gate obrigatório**. Executado no build: "tkinter/ttkbootstrap OK".
- [x] 8.2 No chroot, validar init do TTS: `pyttsx3.init()` + enumeração de vozes (aviso, não gate — a reprodução real via `runAndWait` exige placa de som e é validada no hardware, 9.3). Executado no build: 141 vozes.

## 9. Validação no hardware (Raspberry Pi 4B) — requer o aparelho

- [x] 9.1 Gravar o `.img` no cartão (Pi Imager/`dd`) e arrancar no Pi 4B; confirmar que sobe **direto na calculadora** (sem desktop/login/cursor). — OK em 2026-08-24, após corrigir o tipo MBR da partição de boot para `0x0c`.
- [ ] 9.2 Confirmar a UI `ttkbootstrap` em **tela cheia** no LCD Waveshare 4,3" (800×480), legível.
- [ ] 9.3 Confirmar **TTS pt-BR** anunciando entradas/resultados com a rede desconectada (offline).
- [ ] 9.4 Matar o processo do app e confirmar **auto-restart** (volta a exibir a UI sem reiniciar o Pi).
- [ ] 9.5 (RNF-06) Medir e anotar o tempo de arranque até a UI utilizável para referência futura.

## 10. Documentação

- [x] 10.1 Preencher `system/rpi-os/alpine/README.md`: como **gerar** a imagem, **gravar** no cartão e a **checklist de validação** (passos da seção 9).
- [x] 10.2 Atualizar [docs/build-img-linux.md](../../../docs/build-img-linux.md) adicionando **Alpine** como terceira opção de SO/arranque (ao lado de Pi OS Lite e Buildroot), com prós/contras.
- [x] 10.3 Reforçar em ambos os docs a regra de **não commitar `.img`** (só scripts/config).
