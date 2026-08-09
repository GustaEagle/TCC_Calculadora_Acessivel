## Context

O app (`software/`) já roda: motor em Python + front `ttkbootstrap` (Tkinter) + TTS `pyttsx3`/`espeak-ng`. O que falta é **como o produto arranca no Raspberry Pi 4B**. O PRD deixa isso em aberto (§12) e cobra boot rápido (RNF-06). Hoje só há o `Dockerfile` Debian, bom para desenvolver no PC mas impróprio para embarcar a GUI (ver [docs/build-img-linux.md](../../../docs/build-img-linux.md)).

Esta change entrega uma **imagem `.img` bootável baseada em Alpine Linux aarch64**, gerada por script, que faz o Pi ligar direto na calculadora (kiosk). Restrições que moldam o design:

- **Alvo:** Raspberry Pi 4B, **aarch64**; saída padrão no LCD Waveshare 4,3" HDMI (B), 800×480.
- **Alpine usa musl libc** (não glibc) e **OpenRC/BusyBox init** (não systemd) — muda como se instala Tkinter/TTS e como se faz autologin/kiosk.
- **Tudo offline no aparelho** (RNF-02): nada de instalar pacotes na primeira inicialização via rede.
- **App é imutável nesta change** — só empacotamos e arrancamos `python3 -m software.app`.
- Referência de comportamento kiosk já validada para Pi OS em [docs/build-img-linux.md](../../../docs/build-img-linux.md); aqui adaptamos o mesmo padrão para Alpine.

## Goals / Non-Goals

**Goals:**

- Imagem `.img` **reprodutível a partir de um script** em `system/rpi-os/alpine/`, sem configuração manual no Pi, com o app e dependências **já embutidos** (offline).
- Arranque **kiosk**: autologin no console → X11 mínimo → app em tela cheia → auto-restart; sem desktop, login gráfico ou cursor.
- **TTS pt-BR offline** funcionando sobre musl (`espeak-ng` + `pyttsx3`).
- Base enxuta a favor do RNF-06 (sem serviços supérfluos), sem fixar meta numérica.
- Scripts versionados; `.img` **fora** do Git.

**Non-Goals:**

- Detecção/troca automática HDMI↔LCD (RF-02/RF-09) e `DisplaySelector` — segue stub; a imagem desenha na saída X ativa.
- Drivers de teclado GPIO (matriz 6×7) e leitura do UPS HAT (I2C) — usar o que houver em `hw_platform/`; bring-up pode usar teclado USB.
- Substituir o `Dockerfile` Debian de desenvolvimento (coexiste).
- Meta numérica de boot (RNF-06) — medida depois, no hardware.
- Escopo matemático (PRD §5) e motor `core/` — intocados.

## Decisions

### D1 — Base: Alpine "sys" (root ext4 gravável), não diskless/RAM

Alpine no Pi normalmente arranca em **modo diskless** (roda da RAM, persiste num `.apkovl.tar.gz` via `lbu`). Vamos, em vez disso, instalar Alpine em disco (**modo "sys"**, root ext4 gravável no cartão).

- **Por quê:** o app precisa de `pip install`, home gravável para X/`.xinitrc` e um rootfs previsível. Root gravável simplifica tudo isso e o baking em build.
- **Alternativa considerada:** diskless + `apkovl`. Rejeitada por complicar persistência de `pip`/X e por empurrar instalação de pacotes para o primeiro boot (quebra "offline/reprodutível").
- **Trade-off:** boot marginalmente mais lento que RAM pura, mas muito mais simples; ainda enxuto o bastante para o RNF-06.

### D2 — Imagem montada por script com rootfs "baked" (cross via qemu-binfmt)

O `.img` é produzido por um script em `system/rpi-os/alpine/` que: (1) baixa e verifica o tarball oficial `alpine-rpi-<versão>-aarch64` (partição de boot FAT + kernel `-rpi`/initramfs/dtbs), (2) monta um **rootfs aarch64** fazendo `apk add` dos pacotes e `pip install` das libs **dentro de um chroot emulado com `qemu-aarch64-static`/binfmt** no PC de desenvolvimento, (3) copia `software/` e grava os arquivos de kiosk/config, (4) empacota as partições (FAT boot + ext4 root) num `.img` (via `genimage` ou script `dd`+`mkfs`+`mount`+`cp`).

- **Por quê:** atende "gerado por script", "reprodutível" e "offline no aparelho" (tudo já vem baked). Fixamos versão do Alpine e dos pacotes `apk`/`pip`.
- **Alternativa A:** montar no **próprio Pi** (nativo, sem qemu) e clonar o cartão. Mais simples de acertar (sem binfmt), porém menos "um comando no PC". Fica como **fallback** se o cross incomodar.
- **Alternativa B:** `pi-gen`/Buildroot — já documentadas; fora do pedido (Alpine) e mais pesadas/lentas de montar.
- **Trade-off:** cross-build com qemu pode ter arestas; mitigado pelo fallback nativo (Alternativa A).

### D3 — Boot chain do Pi 4B a partir da partição FAT do Alpine

Reusar o firmware/kernel do tarball `alpine-rpi` (flavor `-rpi`, com `dtbs`). Ajustar na partição FAT:

- `usercfg.txt`/`config.txt`: modo de vídeo do **LCD Waveshare 4,3" B** (seguir [docs/waveshare/4.3inch_HDMI_LCD_B.md](../../../docs/waveshare/README.md)), `disable_overscan`, e KMS (`dtoverlay=vc4-kms-v3d`) ou fallback fbdev.
- `cmdline.txt`: apontar `root=` para a partição ext4 (D1), `console=tty1`, quiet para arranque limpo.
- **Por quê:** não recompilar kernel — o Alpine já traz o kernel do Pi; só configuramos vídeo e root.

### D4 — Kiosk no init do Alpine (OpenRC + BusyBox `inittab`), não systemd

Como Alpine não usa systemd, o autologin sai por **`/etc/inittab`** (respawn de `agetty --autologin kiosk tty1`). O usuário `kiosk` recebe `~/.profile` que dispara `startx` no tty1, e `~/.xinitrc` faz:

```
xset s off -dpms          # tela nunca apaga
unclutter -idle 0 &       # esconder cursor (pacote unclutter/-xfixes)
cd /opt/calculadora
while true; do python3 -m software.app; done   # auto-restart
```

- **Por quê:** replica o padrão kiosk já validado em [docs/build-img-linux.md](../../../docs/build-img-linux.md), traduzido para o mundo OpenRC/`inittab`. O laço `while true` cobre o "Restart=always" sem serviço gráfico.
- **Alternativa considerada:** serviço OpenRC iniciando o X. Rejeitada: exige mexer em permissões do Xwrapper e é mais frágil que `startx` via autologin, igual à ressalva do doc atual.

### D5 — X11 mínimo + Tkinter em musl

Pacotes `apk`: `xorg-server`, `xinit`, `xset`, driver de vídeo (`mesa-dri-gallium` p/ KMS vc4, ou `xf86-video-fbdev`), `libinput`/`eudev` p/ input, `unclutter` (ou `unclutter-xfixes`), fontes (`font-dejavu`), e **`py3-tkinter`** (fornece `_tkinter` ligado ao Tcl/Tk do Alpine). `ttkbootstrap` e `pyttsx3` vêm por **`pip`** (`--break-system-packages`) das versões fixadas em [software/requirements.txt](../../../software/requirements.txt) (pure-Python; sem compilação nativa).

- **Por quê:** `py3-tkinter` do Alpine evita recompilar Tk (mesmo espírito do Dockerfile Debian, que usa `python3-tk` por isso).

### D6 — TTS: `espeak-ng` (não `espeak`) e ligação do `pyttsx3` em musl

Instalar `espeak-ng` (+ `espeak-ng-libs` se existir no repo Alpine) e a cadeia de áudio. O driver espeak do `pyttsx3` carrega a lib por `ctypes`; se ele procurar `libespeak.so.1` e o Alpine só prover `libespeak-ng.so.1`, criar **symlink de compatibilidade**.

- **Por quê:** o `espeak` clássico é incompatível com o `pyttsx3` (falha `SetVoiceByName ... gmw/en`) — regra já registrada no projeto. Voz **pt-BR** definida pelo `speech.py`.
- **Validação obrigatória no build/hardware:** `python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('teste'); e.runAndWait()"`.

### D7 — Áudio direto no ALSA do Pi (sem PulseAudio)

No aparelho o som vai para hardware real (HDMI ou jack 3,5mm), diferente do caso Docker (que roteava ao PulseAudio do host). Instalar `alsa-lib`/`alsa-utils`/`alsa-plugins` e um `/etc/asound.conf` selecionando a saída correta; sem PulseAudio por padrão.

- **Por quê:** menos serviços = mais enxuto (RNF-06). A escolha HDMI×jack depende da fiação/interruptor do LCD e será documentada.

### D8 — Layout no rootfs e versionamento

App em `/opt/calculadora/software/` (cwd `/opt/calculadora`, roda `python3 -m software.app`). Em `system/rpi-os/alpine/` versionar: `build-alpine-img.sh`, `packages` (lista apk), `overlay/` (`.xinitrc`, `.profile`, `inittab`, `asound.conf`, `usercfg.txt`), e `README.md` (gerar + gravar + validar). **Nunca** commitar `.img` (regra do [system/README.md](../../../system/README.md)).

## Risks / Trade-offs

- **[musl × Tkinter/pyttsx3]** → Mitigação: usar `py3-tkinter` do Alpine e `espeak-ng`; validar `import tkinter` e o smoke de TTS ainda no build (chroot) e no hardware. Fallback documentado: método Pi OS Lite de [docs/build-img-linux.md](../../../docs/build-img-linux.md) (app inalterado → troca só o empacotamento).
- **[`pyttsx3` não acha `libespeak-ng` em musl]** → Mitigação: symlink `libespeak.so.1 → libespeak-ng.so.1` e/ou variável de ambiente; teste automatizado no build falha cedo se a voz não inicializar.
- **[Driver de vídeo Pi4 + LCD 800×480]** → vc4-kms-v3d vs fbdev e a modeline do Waveshare podem exigir tentativa/erro. Mitigação: começar pelo `config.txt` do [docs/waveshare](../../../docs/waveshare/README.md); ter fbdev como plano B.
- **[Cross-build qemu-binfmt frágil]** → Mitigação: fallback de build **nativo no Pi** (D2, Alternativa A) documentado no README.
- **[Voz pt-BR no espeak-ng do Alpine]** → qualidade/ids de voz podem diferir. Mitigação: fixar o id de voz em `speech.py`/config e validar no hardware.
- **[Boot não ficar mais rápido que Pi OS Lite]** → Aceitável: o objetivo primário é uma imagem enxuta e reprodutível; a meta numérica do RNF-06 é medida depois e pode redirecionar para Buildroot se necessário.
- **[`unclutter` ausente no repo Alpine]** → usar `unclutter-xfixes` ou esconder cursor via `xsetroot`/opção do X.

## Migration Plan

- **Additivo:** cria `system/rpi-os/alpine/` e atualiza [docs/build-img-linux.md](../../../docs/build-img-linux.md); **não** altera `software/`, testes nem CI.
- **Entrega:** rodar o script → gravar o `.img` (Pi Imager/`dd`) → validar no Pi 4B (checklist: kiosk sobe, app em tela cheia no LCD, TTS fala pt-BR offline, mata o processo e ele reinicia).
- **Rollback:** por ser additivo, basta não usar a imagem Alpine e voltar ao caminho Pi OS Lite já documentado; nenhuma reversão de código é necessária (app não muda).
- **CI:** inalterado — a imagem é validada manualmente no hardware, fora do pipeline de testes Python.

## Open Questions

- **Host de build padrão:** cross no PC (qemu-binfmt) como principal e nativo-no-Pi como fallback — confirmar preferência da equipe.
- **Driver de vídeo:** `vc4-kms-v3d` (KMS/modesetting) ou `xf86-video-fbdev` para o LCD Waveshare 4,3" B?
- **Saída de áudio padrão:** HDMI do LCD ou jack 3,5mm (depende da fiação e do interruptor físico)?
- **Fonte de teclado no bring-up:** USB provisório enquanto a matriz GPIO (fora do escopo) não entra?
- **Versão do Alpine a fixar** (ex.: 3.20/3.21 aarch64) e conjunto exato de pacotes `apk`.
- **Persistência:** confirmar que root gravável "sys" (D1) é aceitável vs. a expectativa de "sem persistência de sessão" do PRD (isso vale para estado do app, não para o SO).
