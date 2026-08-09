# Makefile — atalhos de desenvolvimento da calculadora acessível.
#
# Objetivo: quem clona o repositório roda tudo por aqui, sem decorar comandos.
# Os testes usam unittest (biblioteca padrão do Python), igual ao CI — então
# `make check` roda direto no host, sem instalar nada. O app em si (GUI + TTS)
# roda no Docker (`make up`), porque depende de tkinter/ttkbootstrap/pyttsx3.
# Alvo padrão: `check`.
#
#   make          # equivale a `make check`
#   make check    # roda toda a suíte de testes (unittest, no host)
#   make up        / make down   # abre / fecha o app no Docker (sem setup local)
#   make install   / make run    # cria venv, instala deps e roda o app no host
#   make build    # (re)constrói a imagem Docker do app
#
# Imagem do PRODUTO (SD do Raspberry Pi, Alpine + kiosk) — pede sudo:
#   make rpi-img              # gera a imagem do ZERO (baixa, apk, pip, empacota)
#   make rpi-img CONTINUE=1   # reaproveita o rootfs de .work/ e refaz só o .img
#   make rpi-img-continue     # atalho para o comando acima
#   make rpi-img-clean        # apaga só .work/ (preserva o .img)
#   make rpi-img-distclean    # apaga .work/ E o .img gerado

PYTHON ?= python3
COMPOSE := docker compose
IMAGE := calculadora-acessivel:local
VENV := .venv
VENV_PY := $(VENV)/bin/python

# Imagem Alpine do Raspberry Pi (ver system/rpi-os/alpine/README.md).
RPI_IMG_DIR := system/rpi-os/alpine
RPI_IMG_SCRIPT := ./build-alpine-img.sh
# CONTINUE=1 -> REUSE_ROOTFS=1 no script: pula download/apk/pip/smoke.
CONTINUE ?= 0

.DEFAULT_GOAL := check
.PHONY: check check-docker install run build image up down clean help \
        rpi-img rpi-img-continue rpi-img-clean rpi-img-distclean

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
	@echo "  Debian/Ubuntu:  sudo apt install python3-tk espeak-ng python3-venv"
	@echo "  Depois:  make run     (ou, sem setup nenhum:  make up)"

run: ## Roda o app no host usando o venv criado por `make install`
	$(VENV_PY) -m software.app

build: ## (Re)constrói a imagem Docker do app
	docker build -t $(IMAGE) .

# Pré-requisito interno: garante que a imagem existe antes de subir o app.
image:
	@docker image inspect $(IMAGE) >/dev/null 2>&1 || $(MAKE) build

up: | image ## Abre o app no Docker (janela na tela). Antes: xhost +local:root
	$(COMPOSE) up

down: ## Encerra o app / container
	$(COMPOSE) down

rpi-img: ## Gera a imagem Alpine do Pi (CONTINUE=1 reaproveita o rootfs de .work/)
	@echo "==> Gerando imagem do Raspberry Pi (CONTINUE=$(CONTINUE)) — vai pedir sudo."
	@echo "    Dica: se a sessão gráfica cair, rode num TTY texto (Ctrl+Alt+F3)."
	cd $(RPI_IMG_DIR) && sudo env REUSE_ROOTFS=$(CONTINUE) $(RPI_IMG_SCRIPT) 2>&1 | tee build.log

rpi-img-continue: ## Atalho para `make rpi-img CONTINUE=1` (refaz só o .img)
	@$(MAKE) rpi-img CONTINUE=1

rpi-img-clean: ## Apaga só o diretório de trabalho (.work/) — PRESERVA o .img gerado
	sudo rm -rf $(RPI_IMG_DIR)/.work
	@echo "OK: .work/ removido. O .img (se existir) foi preservado:"
	@ls -lh $(RPI_IMG_DIR)/*.img 2>/dev/null || echo "  (nenhum .img nesta pasta)"

rpi-img-distclean: ## Apaga .work/ E o .img gerado (perde a imagem — use com cuidado)
	sudo rm -rf $(RPI_IMG_DIR)/.work
	rm -f $(RPI_IMG_DIR)/*.img $(RPI_IMG_DIR)/build.log

clean: ## Remove caches de bytecode
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS = ":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
