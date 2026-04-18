# Calculadora científica acessível (TCC)

Calculadora científica com foco em **acessibilidade** (feedback por voz e operação sem depender só da tela), executada em **Raspberry Pi 4B** com teclado físico, **UPS HAT**, painel **LCD 4,3" Waveshare** e suporte a **monitor HDMI**.

**Equipe:** Gustavo, João, Yuri  

**Repositório:** [github.com/GustaEagle/TCC_Calculadora_Acessivel](https://github.com/GustaEagle/TCC_Calculadora_Acessivel)

---

## Documentação principal

| Documento | Descrição |
| --------- | --------- |
| [PRD.md](PRD.md) | Requisitos de produto, escopo e arquitetura em alto nível |
| [Sprints.md](Sprints.md) | Backlog por sprint e estado das tasks |
| [docs/GITHUB_WORKFLOW.md](docs/GITHUB_WORKFLOW.md) | Fluxo Git/GitHub da equipe |
| [docs/REPO_STRUCTURE.md](docs/REPO_STRUCTURE.md) | Mapa de pastas (software, hardware, system) |
| [docs/CONTEXT.md](docs/CONTEXT.md) | Memória curta entre sessões |
| [cronograma/cronograma.md](cronograma/cronograma.md) | Linha do tempo académica |
| [docs/README.md](docs/README.md) | Índice da pasta `docs/` (pinout, Waveshare, CAD, teclado) |

---

## Estrutura do repositório (resumo)

- **`software/`** — Motor de cálculo, UI (LCD / HDMI), acessibilidade (áudio/TTS), plataforma (GPIO, integração)
- **`hardware/`** — PCB (KiCad), snapshots de export para marcos
- **`system/`** — Imagem SO, arranque e scripts (evolução conforme o PRD)
- **`docs/`** — Datasheets, CAD, layout de teclado, notas Waveshare / Pi 4
- **`cronograma/`** — Cronograma em Markdown, HTML interativo e export bruto
- **`prompts/`** — Prompts de sessão (bootstrap, fecho, agentes)
## Estado do projeto

O código de aplicação ainda está em estruturação; o PRD e a documentação de apoio são a referência normativa. Consulte [Sprints.md](Sprints.md) para a sprint corrente e próximos entregáveis.
