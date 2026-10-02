# Calculadora científica acessível (TCC)

Calculadora científica com foco em **acessibilidade** (feedback por voz e operação sem depender só da tela), executada em **Raspberry Pi 4B** com teclado físico, **UPS HAT**, painel **LCD 4,3" Waveshare** e suporte a **monitor HDMI**.

**Equipe:** Gustavo, João, Yuri  

**Repositório:** [github.com/GustaEagle/TCC_Calculadora_Acessivel](https://github.com/GustaEagle/TCC_Calculadora_Acessivel)

---

## Documentação principal

A pasta [`docs/`](docs/README.md) está organizada **por contexto** — comece pelo índice, ou vá direto ao documento:

| Documento | Descrição |
| --------- | --------- |
| [docs/README.md](docs/README.md) | **Índice da documentação** — o que existe e em que pasta |
| [docs/produto/PRD.md](docs/produto/PRD.md) | Requisitos de produto, escopo e arquitetura em alto nível (**normativo**) |
| [docs/guias/teclado-matriz.md](docs/guias/teclado-matriz.md) | **Teclado físico (matriz 6×7)**: as 38 teclas, funções com Ctrl/Shift, GPIO e diagnóstico |
| [docs/guias/comandos-teclado.md](docs/guias/comandos-teclado.md) | Comandos no teclado de PC: Ctrl/Shift, histórico, última resposta |
| [docs/guias/build-img-linux.md](docs/guias/build-img-linux.md) | Arranque em modo kiosk no Raspberry Pi 4B |
| [docs/desenvolvimento/Sprints.md](docs/desenvolvimento/Sprints.md) | Backlog por sprint e estado das tasks |
| [docs/desenvolvimento/GITHUB_WORKFLOW.md](docs/desenvolvimento/GITHUB_WORKFLOW.md) | Fluxo Git/GitHub da equipe |
| [docs/desenvolvimento/REPO_STRUCTURE.md](docs/desenvolvimento/REPO_STRUCTURE.md) | Mapa de pastas (software, hardware, system) |
| [docs/desenvolvimento/CONTEXT.md](docs/desenvolvimento/CONTEXT.md) | Memória curta entre sessões |
| [cronograma/cronograma.md](cronograma/cronograma.md) | Linha do tempo académica |

---

## Executar

```bash
python -m pip install -r software/requirements.txt
python software/app.py
```

`software/app.py` deteta a saída de vídeo ativa e abre **um** front (PRD §7): monitor HDMI externo quando reconhecido, senão o LCD 4,3", e **modo somente áudio** quando não há vídeo utilizável.

Para desenvolvimento e demonstrações a saída pode ser forçada:

```bash
python software/app.py --force-mode hdmi   # front do monitor externo
python software/app.py --force-mode lcd    # front do painel 4,3"
python software/app.py --force-mode audio  # somente voz, sem janela
```

**Histórico:** abre por **Ctrl + Ans** (no PC, a tecla `a` faz o papel do `Ans` da matriz 6x7). Não há botão de histórico — a entrada é sempre pelo teclado.

Lista completa dos atalhos: [docs/guias/teclado-matriz.md](docs/guias/teclado-matriz.md) (teclado do produto) e [docs/guias/comandos-teclado.md](docs/guias/comandos-teclado.md) (teclado de PC).

Testes: `make check` (ou `python -m unittest discover -s software/tests -t .`).

---

## Estrutura do repositório (resumo)

- **`software/`** — Motor de cálculo, UI (LCD / HDMI / partilhada), acessibilidade (áudio/TTS), plataforma (GPIO, integração), ponto de entrada `app.py`
- **`hardware/`** — PCB (KiCad), snapshots de export para marcos
- **`system/`** — Imagem SO, arranque e scripts (evolução conforme o PRD)
- **`docs/`** — Documentação por contexto: `produto/` (PRD), `guias/` (uso e montagem), `desenvolvimento/` (processo), `testes/`, mais referência de hardware (`raspberry-pi-4b/`, `waveshare/`, `keyboard-layout/`, `cad/`)
- **`cronograma/`** — Cronograma em Markdown, HTML interativo e export bruto
- **`prompts/`** — Prompts de sessão (bootstrap, fecho, agentes)

---

## Contribuir

1. Clonar o repositório e entrar na pasta do projeto  
2. Ler [docs/desenvolvimento/GITHUB_WORKFLOW.md](docs/desenvolvimento/GITHUB_WORKFLOW.md) e, no início de cada sessão, seguir [prompts/bootstrap.txt](prompts/bootstrap.txt)  
3. Trabalhar em branch a partir de `main` atualizada; mensagens de commit em **inglês** (ver [.github/COMMIT_GUIDELINES.md](.github/COMMIT_GUIDELINES.md))

---

## Estado do projeto

O código de aplicação ainda está em estruturação; o PRD e a documentação de apoio são a referência normativa. Consulte [docs/desenvolvimento/Sprints.md](docs/desenvolvimento/Sprints.md) para a sprint corrente e próximos entregáveis.
