# Makefile — atalhos de desenvolvimento da calculadora acessível.
#
# Objetivo: quem clona o repositório roda tudo por aqui, sem decorar comandos.
# Os testes usam unittest (biblioteca padrão do Python), igual ao CI — então
# `make check` roda direto no host, sem instalar nada. O app em si (GUI + TTS)
# roda no Docker (`make up`), porque depende de tkinter/ttkbootstrap e da voz
# neural (Piper + cadu); o Docker já baixa a voz no build.
# Alvo padrão: `check`.
#
#   make          # equivale a `make check`
#   make check    # roda toda a suíte de testes (unittest, no host)
#   make up        / make down   # abre / fecha o app no Docker (sem setup local)
#   make install   / make run    # cria venv, instala deps e roda o app no host
#   make build    # (re)constrói a imagem Docker do app
#
# Saída de vídeo: `make run` detecta sozinho (monitor HDMI > LCD > só áudio,
# PRD §7). Para forçar uma saída em desenvolvimento/demonstração:
#   make run-hdmi   # front do monitor externo (responsivo à resolução)
#   make run-lcd    # front do painel 4,3" (800x480)
#   make run-audio  # somente voz, sem janela (RF-04)
#
# Imagem do PRODUTO (SD do Raspberry Pi, Alpine + kiosk) — no Linux pede sudo;
# no Windows roda o mesmo build numa VM Debian do VirtualBox (sem WSL, sem
# reiniciar), via system/rpi-os/alpine/build-alpine-img.ps1:
#   make rpi-img              # gera a imagem do ZERO (baixa, apk, pip, empacota)
#   make rpi-img CONTINUE=1   # reaproveita o rootfs de .work/ e refaz só o .img
#   make rpi-img-continue     # atalho para o comando acima
#   make rpi-img-clean        # apaga só .work/ (preserva o .img)
#   make rpi-img-distclean    # apaga .work/ E o .img gerado
#   make rpi-vm-remove        # (Windows) apaga a VM de build e libera o disco
#
# A voz neural (Piper) precisa de um wheel musl/aarch64 — o build EXIGE que você
# escolha de onde ele vem (senão para com "Sem wheel do Piper"):
#   make piper-wheel                                  # compila o wheel uma vez (-> system/rpi-os/alpine/wheels/)
#   make rpi-img PIPER_WHEEL=.../piper_tts-*.whl      # usa um wheel já compilado (rápido)
#   make rpi-img PIPER_BUILD_IN_CHROOT=1              # compila o wheel dentro do build (lento)
# Fixe também CADU_ONNX_SHA256/CADU_JSON_SHA256 (a voz é baixada com sha256).
#
# Bring-up do TECLADO físico 6x7 — estes alvos rodam NO Raspberry Pi (por SSH),
# não no PC de desenvolvimento, porque precisam dos GPIO reais do header J8:
#   make keypad-pins           # imprime a pinagem esperada (roda em qualquer lugar)
#   make keypad-scan           # varre a matriz: cada tecla premida aparece na consola
#   make keypad-toggle LINE=C3 # pisca um condutor para o achar no flat com multímetro

VENV := .venv

# No Windows nao ha 'python3' (so o stub da Microsoft Store) e o venv guarda
# os executaveis em Scripts/, nao bin/ - por isso os dois variam com $(OS),
# a variavel de ambiente que o GNU Make para Windows sempre define.
ifeq ($(OS),Windows_NT)
PYTHON ?= python
VENV_PY := $(VENV)/Scripts/python.exe
else
PYTHON ?= python3
VENV_PY := $(VENV)/bin/python
endif
COMPOSE := docker compose
IMAGE := calculadora-acessivel:local

# Bring-up do teclado (software/tools/keypad_bringup.py). Sem venv de propósito:
# no Pi a biblioteca de GPIO é pacote de sistema (sudo apt install python3-lgpio)
# e o .venv deste repositório nem existe lá.
KEYPAD_TOOL := software/tools/keypad_bringup.py
# Condutor que `keypad-toggle` pisca (L1..L6 = linhas, C1..C7 = colunas).
LINE ?= L1
# gpiochip do SoC: 0 no Pi 4B (o alvo deste TCC), 4 no Pi 5.
CHIP ?= 0

# Imagem Alpine do Raspberry Pi (ver system/rpi-os/alpine/README.md).
RPI_IMG_DIR := system/rpi-os/alpine
RPI_IMG_SCRIPT := ./build-alpine-img.sh
# CONTINUE=1 -> REUSE_ROOTFS=1 no script: pula download/apk/pip/smoke.
CONTINUE ?= 0
# Voz neural (Piper) no build da imagem. Escolha UM:
#   PIPER_WHEEL=/caminho/piper_tts-*.whl  -> usa um wheel musl/aarch64 pronto (rápido)
#   PIPER_BUILD_IN_CHROOT=1               -> compila o wheel no chroot (lento sob qemu)
PIPER_WHEEL ?=
PIPER_BUILD_IN_CHROOT ?=
# sha256 fixo da voz cadu (repassados ao build; obrigatórios na imagem).
CADU_ONNX_SHA256 ?=
CADU_JSON_SHA256 ?=
# No Windows o build roda numa VM do VirtualBox, orquestrada por este script.
RPI_IMG_PS := powershell -NoProfile -ExecutionPolicy Bypass -File $(RPI_IMG_DIR)/build-alpine-img.ps1

.DEFAULT_GOAL := check
.PHONY: check check-docker install run run-hdmi run-lcd run-audio \
        build image up down clean help \
        piper-wheel rpi-img rpi-img-continue rpi-img-clean rpi-img-distclean rpi-vm-remove \
        keypad-pins keypad-scan keypad-toggle

check: ## Roda toda a suíte de testes com unittest (igual ao CI)
	$(PYTHON) -m unittest discover -s software/tests -t . -v

check-docker: | image ## Roda os testes dentro do container (ambiente isolado)
	docker run --rm -v "$(CURDIR)/software:/app/software" -w /app $(IMAGE) \
		python3 -B -m unittest discover -s software/tests -t . -v

install: ## Cria um venv (.venv) e instala as deps Python do app — evita o PEP 668
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r software/requirements.txt
	@echo ""
	@echo "OK. O app tambem precisa de pacotes de SISTEMA (nao vem por pip):"
	@echo "  Debian/Ubuntu:  sudo apt install python3-tk espeak-ng alsa-utils python3-venv"
	@echo "  E da voz neural cadu (Piper) no caminho padrao:"
	@echo "    sudo scripts/download-piper-voice.sh /opt/piper/voices"
	@echo "    (sem a voz, o app fala pelo fallback espeak-ng — WRN-011)"
	@echo "  Depois:  make run     (ou, sem setup nenhum:  make up)"

run: ## Roda o app no host usando o venv criado por `make install`
	$(VENV_PY) -m software.app

# Atalhos de --force-mode: pulam a detecção do DisplaySelector (PRD §7) e abrem
# uma saída específica. Úteis para desenvolver/demonstrar sem o hardware.
run-hdmi: ## Força o front do monitor externo (janela responsiva)
	$(VENV_PY) -m software.app --force-mode hdmi

run-lcd: ## Força o front do painel LCD 4,3" (800x480)
	$(VENV_PY) -m software.app --force-mode lcd

run-audio: ## Força o modo somente áudio (RF-04) — sem janela, só voz
	$(VENV_PY) -m software.app --force-mode audio

build: ## (Re)constrói a imagem Docker do app
	docker build -t $(IMAGE) .

# Pré-requisito interno: garante que a imagem existe antes de subir o app.
image:
	@docker image inspect $(IMAGE) >/dev/null 2>&1 || $(MAKE) build

up: | image ## Abre o app no Docker (janela na tela). Antes: xhost +local:root
	$(COMPOSE) up

down: ## Encerra o app / container
	$(COMPOSE) down

piper-wheel: ## Compila o wheel musl/aarch64 do Piper p/ a imagem (-> system/rpi-os/alpine/wheels/)
	scripts/build-piper-wheel.sh

rpi-img: ## Gera a imagem Alpine do Pi (precisa PIPER_WHEEL=... ou PIPER_BUILD_IN_CHROOT=1; CONTINUE=1 reusa .work/)
ifeq ($(OS),Windows_NT)
	@echo "==> Gerando imagem do Raspberry Pi pelo Windows (VM VirtualBox, CONTINUE=$(CONTINUE))."
	$(RPI_IMG_PS) -Action $(if $(filter 1,$(CONTINUE)),continue,build)
else
	@echo "==> Gerando imagem do Raspberry Pi (CONTINUE=$(CONTINUE)) — vai pedir sudo."
	@echo "    Dica: se a sessão gráfica cair, rode num TTY texto (Ctrl+Alt+F3)."
	cd $(RPI_IMG_DIR) && sudo env REUSE_ROOTFS=$(CONTINUE) \
		PIPER_WHEEL="$(PIPER_WHEEL)" PIPER_BUILD_IN_CHROOT="$(PIPER_BUILD_IN_CHROOT)" \
		CADU_ONNX_SHA256="$(CADU_ONNX_SHA256)" CADU_JSON_SHA256="$(CADU_JSON_SHA256)" \
		$(RPI_IMG_SCRIPT) 2>&1 | tee build.log
endif

rpi-img-continue: ## Atalho para `make rpi-img CONTINUE=1` (refaz só o .img)
	@$(MAKE) rpi-img CONTINUE=1

rpi-img-clean: ## Apaga só o diretório de trabalho (.work/) — PRESERVA o .img gerado
ifeq ($(OS),Windows_NT)
	$(RPI_IMG_PS) -Action clean
else
	sudo rm -rf $(RPI_IMG_DIR)/.work
	@echo "OK: .work/ removido. O .img (se existir) foi preservado:"
	@ls -lh $(RPI_IMG_DIR)/*.img 2>/dev/null || echo "  (nenhum .img nesta pasta)"
endif

rpi-img-distclean: ## Apaga .work/ E o .img gerado (perde a imagem — use com cuidado)
ifeq ($(OS),Windows_NT)
	$(RPI_IMG_PS) -Action distclean
else
	sudo rm -rf $(RPI_IMG_DIR)/.work
	rm -f $(RPI_IMG_DIR)/*.img $(RPI_IMG_DIR)/build.log
endif

rpi-vm-remove: ## (Windows) Apaga a VM VirtualBox de build e libera o disco
ifeq ($(OS),Windows_NT)
	$(RPI_IMG_PS) -Action vm-remove
else
	@echo "Nada a fazer: a VM de build so existe no fluxo do Windows (build-alpine-img.ps1)."
endif

keypad-pins: ## Pinagem esperada do chicote do teclado (não toca no hardware)
	$(PYTHON) $(KEYPAD_TOOL) --list

keypad-scan: ## (no Pi) Varre a matriz 6x7; prima as teclas, Ctrl-C imprime o mapa
	$(PYTHON) $(KEYPAD_TOOL) --chip $(CHIP)

keypad-toggle: ## (no Pi) Pisca um condutor p/ o achar no flat: make keypad-toggle LINE=C3
	$(PYTHON) $(KEYPAD_TOOL) --chip $(CHIP) --toggle $(LINE)

clean: ## Remove caches de bytecode
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS = ":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
