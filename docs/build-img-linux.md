# Rodar a calculadora como sistema embarcado (kiosk) no Raspberry Pi 4B

Objetivo: ao **ligar o Pi, ele arranca direto no aplicativo** da calculadora —
sem mostrar o SO, desktop ou terminal. Referência: [PRD.md](../../PRD.md) §12
(SO/arranque) e RNF-06 (boot rápido).

---

## Duas decisões distintas

1. **Como o app arranca sozinho (modo kiosk)** — é o trabalho de verdade;
   funciona igual em qualquer base de SO.
2. **Como empacotar/distribuir** — imagem Linux pronta vs instalar no Pi OS.
   É só "como entregar", não muda o comportamento.

---

## Opções de empacotamento

| Abordagem | Boot | Esforço | Recomendação |
| --------- | ---- | ------- | ------------ |
| **Pi OS Lite + kiosk** | ~15–25 s | Baixo | ✅ Começar por aqui |
| **Buildroot** (`system/buildroot/`) | ~3–8 s | Alto | ⚠️ Só se precisar provar boot ultrarrápido (RNF-06) |
| **Docker no Pi** | Lento | Médio | ❌ Não usar no produto (bom só p/ testar no PC) |

> "Gerar uma imagem que tenha ela" **não** exige Buildroot: configure o Pi OS
> Lite uma vez, valide, e **clone o cartão para um `.img`** (ver abaixo). Isso já
> é uma imagem Linux com o app embutido, reprodutível e sem a dor do Buildroot.
>
> **Docker não é forma de embarcar** GUI no aparelho final — foi útil apenas
> para desenvolvimento/teste no PC.

---

## Como o kiosk funciona (Pi OS Lite)

O app é Tkinter, então precisa de um X11 mínimo — mas **sem desktop**, só o app:

```
Liga o Pi
  → Autologin no console (raspi-config → Boot → Console Autologin)
  → systemd (ou ~/.xinitrc) inicia:  python3 -m software.app
  → Só a janela da calculadora na tela (sem menu, sem barra)
```

Para appliance de verdade, prefira **systemd com Restart=always** (reinicia o app
se ele cair) em vez do `.xinitrc` simples.

---

## Passo a passo (Pi OS Lite + kiosk via systemd)

1. **Gravar Pi OS Lite (64-bit)** no cartão (Raspberry Pi Imager).

2. **Instalar dependências** no Pi:
   ```bash
   sudo apt update
   sudo apt install -y xserver-xorg xinit python3-tk espeak python3-pip unclutter
   pip3 install --break-system-packages ttkbootstrap pyttsx3
   ```

3. **Copiar o código** para o Pi (ex.: `/home/pi/calculadora/`, contendo a pasta
   `software/`).

4. **Autologin no console:** `sudo raspi-config` → *System Options* →
   *Boot / Auto Login* → **Console Autologin**.

5. **Criar o serviço** `/etc/systemd/system/calculadora.service`:
   ```ini
   [Unit]
   Description=Calculadora Acessivel (kiosk)
   After=systemd-user-sessions.service

   [Service]
   User=pi
   WorkingDirectory=/home/pi/calculadora
   Environment=DISPLAY=:0
   # startx sobe um X mínimo e executa só o app como cliente
   ExecStart=/usr/bin/startx /usr/bin/python3 -m software.app
   Restart=always
   RestartSec=2

   [Install]
   WantedBy=multi-user.target
   ```

6. **Habilitar e reiniciar:**
   ```bash
   sudo systemctl enable calculadora.service
   sudo reboot
   ```

Ao voltar, o Pi arranca direto na calculadora.

---

## Ajustes recomendados de appliance

- **Sem blanking de tela:** no X, `xset s off -dpms` (adicionar antes do app).
- **Esconder cursor:** `unclutter -idle 0` (já instalado no passo 2).
- **Áudio:** garantir saída correta (`raspi-config` → *Audio*) para o TTS pt-BR.
- **HDMI/LCD:** a lógica de `DisplaySelector` (RF-02) ainda é stub; o kiosk
  desenha na saída ativa do X. Detecção/troca automática é trabalho à parte.

---

## Gerar uma imagem distribuível (.img)

Depois de tudo configurado e validado:

1. Desligar o Pi, remover o cartão, inserir no PC.
2. Clonar para arquivo (Linux):
   ```bash
   sudo dd if=/dev/sdX of=calculadora.img bs=4M status=progress
   ```
   (ou usar *Pi Imager* / *rpi-clone*).
3. Opcional: encolher a imagem com `pishrink` para caber em cartões menores.

> **Não commitar `.img` no Git** (regra do [system/README.md](../README.md)):
> versione apenas os scripts/config deste diretório e documente como gerar.

---

## Criar a imagem do zero (reprodutível)

Clonar o cartão (seção acima) é rápido, mas depende de você ter configurado o Pi
"na mão". Para uma imagem **reprodutível a partir do zero** — que qualquer pessoa
regenera só rodando um build — há duas vias:

| Via | O que gera | Esforço | Quando escolher |
| --- | ---------- | ------- | --------------- |
| **pi-gen** | Imagem baseada no Pi OS, montada por script | Médio | ✅ Reprodutível sem sair do ecossistema Pi OS |
| **Buildroot** | Linux mínimo do zero (kernel + rootfs custom) | Alto | ⚠️ Só p/ boot ultrarrápido / appliance enxuto (RNF-06) |

### Via A — pi-gen (Pi OS montado por script)

`pi-gen` é a ferramenta oficial que constrói as imagens do Raspberry Pi OS. Você
adiciona um "estágio" próprio que instala o app e o kiosk — o resultado é um
`.img` gerado 100% por script, sem configuração manual.

1. Clonar e preparar:
   ```bash
   git clone https://github.com/RPi-Distro/pi-gen
   cd pi-gen
   ```
2. Criar um estágio `stage-calculadora/` com:
   - `00-packages` — lista de pacotes apt (`xserver-xorg xinit python3-tk espeak unclutter`).
   - `01-run.sh` — copia a pasta `software/`, cria o `calculadora.service` e habilita
     autologin (os mesmos passos 3–6 da seção kiosk, mas em script).
3. Definir `config` (nome da imagem, `TARGET_HOSTNAME`, usuário) e rodar:
   ```bash
   sudo ./build.sh
   ```
4. A imagem sai em `deploy/*.img` — pronta para gravar com o Pi Imager.

> Vantagem: o build é o "código" da imagem. Versione o estágio
> `stage-calculadora/` em `system/rpi-os/` (não o `.img`).

### Via B — Buildroot (Linux do zero)

Constrói um sistema mínimo só com o necessário para o app. Boot em segundos, mas
é a via mais trabalhosa — Tkinter, X e TTS precisam ser habilitados manualmente e
alguns pacotes Python não existem prontos no Buildroot. Os artefatos reutilizáveis
(defconfig, overlay) ficam em [system/buildroot/](../buildroot/).

1. Obter o Buildroot e partir do defconfig do Pi 4 (64-bit):
   ```bash
   git clone https://gitlab.com/buildroot.org/buildroot
   cd buildroot
   make raspberrypi4_64_defconfig
   ```
2. `make menuconfig` e habilitar:
   - **Toolchain:** headers/compilador compatíveis.
   - **Target packages → Interpreter languages:** `python3` + a opção **tkinter**.
   - **Graphic libraries → X.org:** servidor X mínimo (xserver + xinit).
   - **Audio/misc:** `espeak` (para o TTS).
   - **System:** init (systemd **ou** BusyBox) e autologin.
3. **App + dependências Python:** `ttkbootstrap` e `pyttsx3` não são pacotes
   nativos do Buildroot. Opções:
   - criar um *package* Buildroot para cada um, **ou**
   - usar um **rootfs overlay** (`system/buildroot/overlay/`) com o `software/` e
     as libs Python já instaladas, mais um script de init que executa
     `startx python3 -m software.app`.
4. Construir a imagem:
   ```bash
   make
   ```
   O resultado (`output/images/sdcard.img`) já é a imagem final.
5. Gravar no cartão com `dd` (mesmo comando da seção `.img`).

> **Honestidade de prazo:** para o TCC, comece pela **Via A (pi-gen)** ou pelo
> kiosk simples. O Buildroot só compensa se boot ultrarrápido for um **resultado
> a demonstrar** — o cross-build de Tkinter + X + TTS consome tempo real.
