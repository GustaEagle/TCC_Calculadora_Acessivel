# Documentação do projeto (`docs/`)

Índice da documentação do TCC — **calculadora científica acessível** em Raspberry Pi 4B.

A pasta está organizada **por contexto**: cada subpasta responde a uma pergunta diferente. Procure primeiro pela pergunta, depois pelo ficheiro.

| Pasta | Responde a | Conteúdo |
| ----- | ---------- | -------- |
| [produto/](produto/) | *O que o produto deve fazer?* | PRD (referência normativa) e materiais/métodos do TCC |
| [guias/](guias/) | *Como se usa e como se faz rodar?* | Teclado da matriz, teclado de PC, imagem de arranque (kiosk) no Pi |
| [desenvolvimento/](desenvolvimento/) | *Como a equipe trabalha?* | Fluxo Git, mapa do repositório, backlog, memória de sessão, registo semanal |
| [testes/](testes/) | *O que já foi validado?* | Relatórios de testes e roteiro de usabilidade |
| [raspberry-pi-4b/](raspberry-pi-4b/) | *Como é a placa?* | Pinout do header J8 (40 pinos), datasheet, diagrama |
| [waveshare/](waveshare/) | *Como são os periféricos?* | LCD 4,3" HDMI (B) e UPS HAT |
| [keyboard-layout/](keyboard-layout/) | *Como é o teclado?* | Layout da matriz 6×7 no formato KLE |
| [cad/](cad/) | *Como as peças se encaixam?* | Modelos 3D (STEP/SLDPRT) do Pi, LCD e UPS HAT |

---

## Por onde começar

- **Chegou agora ao projeto:** [produto/PRD.md](produto/PRD.md) §1 (resumo) → [desenvolvimento/REPO_STRUCTURE.md](desenvolvimento/REPO_STRUCTURE.md) → [desenvolvimento/GITHUB_WORKFLOW.md](desenvolvimento/GITHUB_WORKFLOW.md).
- **Vai programar nesta sessão:** [desenvolvimento/CONTEXT.md](desenvolvimento/CONTEXT.md) (onde a última sessão parou) → [desenvolvimento/Sprints.md](desenvolvimento/Sprints.md) (task em aberto).
- **Vai mexer no hardware:** [raspberry-pi-4b/pinout.md](raspberry-pi-4b/pinout.md) §6 (matriz do teclado) → [keyboard-layout/README.md](keyboard-layout/README.md).
- **Vai montar o aparelho:** [guias/build-img-linux.md](guias/build-img-linux.md) → [waveshare/README.md](waveshare/README.md).

---

## Documentos mais consultados

| Documento | Para quê |
| --------- | -------- |
| [produto/PRD.md](produto/PRD.md) | Requisitos, escopo e arquitetura — **normativo**; desvios exigem atualizar o PRD |
| [guias/teclado-matriz.md](guias/teclado-matriz.md) | **Teclado físico do produto**: as 38 teclas da matriz 6×7 e o que cada uma faz |
| [guias/comandos-teclado.md](guias/comandos-teclado.md) | Os mesmos comandos no teclado de PC (desenvolvimento e testes) |
| [raspberry-pi-4b/pinout.md](raspberry-pi-4b/pinout.md) | Pinagem J8 e atribuição de GPIO da matriz (contrato com o código) |
| [desenvolvimento/GITHUB_WORKFLOW.md](desenvolvimento/GITHUB_WORKFLOW.md) | Branches, PRs e sequência de comandos da equipe |
| [desenvolvimento/sessoes/](desenvolvimento/sessoes/README.md) | O que cada pessoa fez, por semana do plano |

---

## Fora de `docs/`

| Caminho | Conteúdo |
| ------- | -------- |
| [`../README.md`](../README.md) | Visão geral do repositório e como executar |
| [`../cronograma/`](../cronograma/) | Linha do tempo académica (Markdown + HTML interativo) |
| [`../prompts/`](../prompts/) | Prompts de sessão (bootstrap, fecho, agentes) |
| [`../openspec/`](../openspec/) | Propostas de mudança e specs vigentes |
| [`../.github/COMMIT_GUIDELINES.md`](../.github/COMMIT_GUIDELINES.md) | Convenção de mensagens de commit |

---

## Convenções desta pasta

- **Um contexto por pasta.** Documento novo entra na pasta que responde à mesma pergunta; se não houver, discuta antes de criar pasta nova.
- **Links relativos**, sempre — o repositório é lido tanto no GitHub como offline no clone.
- **Ficheiros binários** (datasheet, CAD, imagens) ficam junto do documento que os explica, não numa pasta genérica de anexos.
