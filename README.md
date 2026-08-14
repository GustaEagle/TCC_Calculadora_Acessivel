# Calculadora científica acessível (TCC)

Calculadora científica com foco em **acessibilidade** (feedback por voz e operação sem depender só da tela), executada em **Raspberry Pi 4B** com teclado físico, **UPS HAT**, painel **LCD 4,3" Waveshare** e suporte a **monitor HDMI**.

**Equipe:** Gustavo, João, Yuri  

**Repositório:** [github.com/GustaEagle/TCC_Calculadora_Acessivel](https://github.com/GustaEagle/TCC_Calculadora_Acessivel)

---

## Documentação principal

| Documento | Descrição |
| --------- | --------- |
| [PRD.md](PRD.md) | Requisitos de produto, escopo e arquitetura em alto nível |
| [Calculadora rev04.docx](Calculadora%20rev04.docx) | Parte escrita do TCC (revisão 04, Microsoft Word) |
| [Sprints.md](Sprints.md) | Backlog por sprint e estado das tasks |
| [docs/GITHUB_WORKFLOW.md](docs/GITHUB_WORKFLOW.md) | Fluxo Git/GitHub da equipe |
| [docs/REPO_STRUCTURE.md](docs/REPO_STRUCTURE.md) | Mapa de pastas (software, hardware, system) |
| [docs/CONTEXT.md](docs/CONTEXT.md) | Memória curta entre sessões |
| [cronograma/cronograma.md](cronograma/cronograma.md) | Linha do tempo académica |
| [docs/README.md](docs/README.md) | Índice da pasta `docs/` (pinout, Waveshare, CAD, teclado) |

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

Testes: `make check` (ou `python -m unittest discover -s software/tests -t .`).

---

## Estrutura do repositório (resumo)

- **`software/`** — Motor de cálculo, UI (LCD / HDMI / partilhada), acessibilidade (áudio/TTS), plataforma (GPIO, integração), ponto de entrada `app.py`
- **`hardware/`** — PCB (KiCad), snapshots de export para marcos
- **`system/`** — Imagem SO, arranque e scripts (evolução conforme o PRD)
- **`docs/`** — Datasheets, CAD, layout de teclado, notas Waveshare / Pi 4
- **`cronograma/`** — Cronograma em Markdown, HTML interativo e export bruto
- **`prompts/`** — Prompts de sessão (bootstrap, fecho, agentes)

---

## Contribuir

1. Clonar o repositório e entrar na pasta do projeto  
2. Ler [docs/GITHUB_WORKFLOW.md](docs/GITHUB_WORKFLOW.md) e, no início de cada sessão, seguir [prompts/bootstrap.txt](prompts/bootstrap.txt)  
3. Trabalhar em branch a partir de `main` atualizada; mensagens de commit em **inglês** (ver [.github/COMMIT_GUIDELINES.md](.github/COMMIT_GUIDELINES.md) se existir)

---

## Estado do projeto

O código de aplicação ainda está em estruturação; o PRD e a documentação de apoio são a referência normativa. Consulte [Sprints.md](Sprints.md) para a sprint corrente e próximos entregáveis.
