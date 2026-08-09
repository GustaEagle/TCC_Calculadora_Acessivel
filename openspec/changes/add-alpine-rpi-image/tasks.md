## 1. Estrutura e versionamento

- [ ] 1.1 Criar `system/rpi-os/alpine/` com subpastas `overlay/` (arquivos que vão para o rootfs) e `README.md` (esqueleto).
- [ ] 1.2 Adicionar/confirmar no `.gitignore` a exclusão de artefatos de imagem (`*.img`, `*.img.gz`, diretórios de work/mount do build) sob `system/rpi-os/alpine/`.
- [ ] 1.3 Criar `system/rpi-os/alpine/packages` com a lista de pacotes `apk` (um por linha) e um comentário com a **versão do Alpine fixada** (ex.: 3.x aarch64).

## 2. Base e dependências (decisões D1, D5, D6, D7)

- [ ] 2.1 Fixar a versão do Alpine e a URL/checksum do tarball `alpine-rpi-<ver>-aarch64` no script de build (verificação de hash obrigatória).
- [ ] 2.2 Preencher `packages` com: `python3 py3-tkinter`, `espeak-ng` (+ `espeak-ng-libs` se existir), `alsa-lib alsa-utils alsa-plugins`, `xorg-server xinit xset`, driver de vídeo (`mesa-dri-gallium` p/ vc4-kms **ou** `xf86-video-fbdev`), `libinput eudev`, `unclutter` (ou `unclutter-xfixes`), `font-dejavu`, `py3-pip`.
- [ ] 2.3 Registrar as libs Python via `pip` a partir de [software/requirements.txt](../../../software/requirements.txt) (`ttkbootstrap==1.20.4`, `pyttsx3==2.99`), com `--break-system-packages`.

## 3. Script de build da imagem (decisão D2)

- [ ] 3.1 Escrever `system/rpi-os/alpine/build-alpine-img.sh` que baixa+verifica o tarball, prepara a **partição FAT de boot** (kernel `-rpi`/initramfs/dtbs) e cria o **rootfs ext4 "sys"** (D1).
- [ ] 3.2 Montar o rootfs aarch64 em **chroot com `qemu-aarch64-static`/binfmt** e executar `apk add` (lista do passo 2.2) + `pip install` (passo 2.3) — tudo baked, **sem** instalação por rede no primeiro boot.
- [ ] 3.3 Empacotar as duas partições num `.img` (via `genimage` ou script `dd`+`mkfs`+`mount`+`cp`); a imagem final não é versionada.
- [ ] 3.4 Documentar no script o **fallback de build nativo no Pi** (Alternativa A do D2) para o caso de o cross/binfmt falhar.

## 4. Boot e vídeo do Pi 4B (decisão D3)

- [ ] 4.1 Gerar `usercfg.txt`/`config.txt` na partição de boot com o modo do **LCD Waveshare 4,3" B** (seguir [docs/waveshare/README.md](../../../docs/waveshare/README.md)), `disable_overscan` e `dtoverlay=vc4-kms-v3d` (com fbdev como plano B).
- [ ] 4.2 Ajustar `cmdline.txt`: `root=` para a partição ext4, `console=tty1` e arranque silencioso (quiet), sem prompt visível.

## 5. Kiosk: autologin + X + auto-restart (decisão D4)

- [ ] 5.1 Criar usuário `kiosk` no rootfs e configurar autologin no `tty1` via `/etc/inittab` (`agetty --autologin kiosk`), sem getty de login visível.
- [ ] 5.2 Adicionar `overlay/home/kiosk/.profile` que dispara `startx` apenas no `tty1`.
- [ ] 5.3 Adicionar `overlay/home/kiosk/.xinitrc` com `xset s off -dpms`, ocultação de cursor (`unclutter -idle 0` ou equivalente) e o laço `while true; do python3 -m software.app; done` (auto-restart) a partir de `/opt/calculadora`.
- [ ] 5.4 Garantir que nenhum desktop/display manager é instalado ou habilitado (requisito "arranque enxuto").

## 6. Áudio e TTS offline (decisões D6, D7)

- [ ] 6.1 Adicionar `overlay/etc/asound.conf` selecionando a saída de áudio do Pi (HDMI **ou** jack — decidir e documentar).
- [ ] 6.2 Se o `pyttsx3` procurar `libespeak.so.1`, criar symlink de compatibilidade para `libespeak-ng.so.1` no rootfs.
- [ ] 6.3 Confirmar/fixar a voz **pt-BR** usada pelo `speech.py` no ambiente `espeak-ng` do Alpine.

## 7. Baking do app no rootfs (decisão D8)

- [ ] 7.1 Copiar `software/` para `/opt/calculadora/software/` no rootfs (sem `.venv`, `__pycache__`, testes opcionais).
- [ ] 7.2 Definir o working dir de execução em `/opt/calculadora` para que `python3 -m software.app` resolva o pacote `software`.

## 8. Validação automática no build (chroot)

- [ ] 8.1 No chroot, rodar smoke de GUI headless-friendly: `python3 -c "import tkinter, ttkbootstrap"` sem erro (import de `_tkinter` em musl).
- [ ] 8.2 No chroot, rodar smoke de TTS: `python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('teste'); e.runAndWait()"` — build **falha** se a voz não inicializar (regra `espeak-ng`, não `espeak`).

## 9. Validação no hardware (Raspberry Pi 4B)

- [ ] 9.1 Gravar o `.img` no cartão (Pi Imager/`dd`) e arrancar no Pi 4B; confirmar que sobe **direto na calculadora** (sem desktop/login/cursor).
- [ ] 9.2 Confirmar a UI `ttkbootstrap` em **tela cheia** no LCD Waveshare 4,3" (800×480), legível.
- [ ] 9.3 Confirmar **TTS pt-BR** anunciando entradas/resultados com a rede desconectada (offline).
- [ ] 9.4 Matar o processo do app e confirmar **auto-restart** (volta a exibir a UI sem reiniciar o Pi).
- [ ] 9.5 (RNF-06) Medir e anotar o tempo de arranque até a UI utilizável para referência futura.

## 10. Documentação

- [ ] 10.1 Preencher `system/rpi-os/alpine/README.md`: como **gerar** a imagem, **gravar** no cartão e a **checklist de validação** (passos da seção 9).
- [ ] 10.2 Atualizar [docs/build-img-linux.md](../../../docs/build-img-linux.md) adicionando **Alpine** como terceira opção de SO/arranque (ao lado de Pi OS Lite e Buildroot), com prós/contras.
- [ ] 10.3 Reforçar em ambos os docs a regra de **não commitar `.img`** (só scripts/config).
