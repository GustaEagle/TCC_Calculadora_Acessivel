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

PYTHON ?= python3
COMPOSE := docker compose
IMAGE := calculadora-acessivel:local
VENV := .venv
VENV_PY := $(VENV)/bin/python

.DEFAULT_GOAL := check
.PHONY: check check-docker install run build image up down clean help

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

clean: ## Remove caches de bytecode
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS = ":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
