# Fluxo Git e GitHub — equipe (TCC Calculadora)

Padronização para **Gustavo**, **João** e **Yuri**: versionamento, início/fim de sessão e contexto compartilhado. Complementa os prompts em [`Prompts/bootstrap.txt`](../Prompts/bootstrap.txt) e [`Prompts/close-session.txt`](../Prompts/close-session.txt).

---

## 1. Papéis dos artefatos

| Artefato | Função |
| -------- | ------ |
| [`PRD.md`](../PRD.md) | Requisitos e escopo do produto (normativo). |
| [`Cronograma/cronograma.md`](../Cronograma/cronograma.md) | Linha do tempo acadêmica (professor). |
| [`Cronograma/cronograma.html`](../Cronograma/cronograma.html) | Visualização interativa + Gantt (abrir no navegador). |
| [`docs/sessoes/`](sessoes/README.md) | Registro semanal agregado por pessoa (fim de sessão). |
| [`Sprints.md`](../Sprints.md) | Backlog por sprint: tasks, responsáveis, status. |
| [`docs/CONTEXT.md`](CONTEXT.md) | Memória curta: última sessão, pendências, próximo foco. |
| [`TCC.txt`](../TCC.txt) | Texto acadêmico legado (funções, materiais). |
| [`docs/README.md`](README.md) | Índice da documentação técnica. |

Regra: **não inventar escopo** no `Sprints.md`; desvios grandes exigem atualização do `PRD.md` (e alinhamento com o cronograma).

---

## 2. Branches e nomes

- **`main`**: branch estável, sempre integrável. Proteger no GitHub (review opcional, conforme política da turma).
- **Trabalho diário**: branch a partir de `main` atualizada.

Sugestão de nome (escolham uma convenção e mantenham):

- `feature/<slug-curto>` — nova funcionalidade ou entregável.
- `docs/<slug>` — só documentação.
- `hardware/<slug>` — esquemático, PCB, layout de teclado, etc.

Exemplos: `feature/ui-lcd-basica`, `docs/pinout-revisao`, `hardware/teclado-v2`.

Evitar branches longas sem merge; integrem em `main` com frequência.

---

## 3. `Sprints.md`, `main` e trabalho em equipe

### Onde fica a “verdade” do sprint?

- **`Sprints.md`** é o backlog operacional combinado pela equipe.
- A versão **compartilhada e atual** é a que está em **`main` no GitHub** **depois** do merge do PR (ou merge local equivalente).
- No dia a dia vocês alteram `Sprints.md` na **branch de trabalho** (`feature/...`, etc.), fazem **commit** e integram em `main` via **PR**. Não é necessário editar direto em `main` no computador; o importante é que **todo mundo passe a enxergar as mudanças** quando elas entram em `main` e cada um dá **`git pull`** antes de continuar.

### Fluxo sequencial (ex.: Gustavo faz X; João depois faz Y em cima de X)

1. Gustavo: commits na branch dele → `push` → **Pull Request** para `main` → **merge** após revisão (ou política acordada).
2. João, **antes** de desenvolver Y:

```powershell
git checkout main
git pull origin main
git checkout -b feature/joao-y
# branch já existente:
# git checkout feature/joao-y
# git fetch origin
# git merge origin/main
```

Assim o clone de João inclui **código e `Sprints.md`** já atualizados com o trabalho de Gustavo **que já foi integrados em `main`**.

Se o PR do Gustavo ainda **não** foi mergeado, João pode trabalhar em paralelo, mas **não** verá o X no `main` até o merge — opções: esperar o merge, ou temporariamente puxar a branch do Gustavo (`git fetch` + `git merge origin/feature/gustavo-x`) **só se** combinarem esse fluxo (mais avançado).

### Fluxo paralelo (dois ou mais ao mesmo tempo)

- Cada pessoa: `git checkout main` → `git pull origin main` → `git checkout -b feature/<slug-unico>`.
- Commits independentes; PRs separados para `main`.
- **Arquivos diferentes:** merges em `main` tendem a ser automáticos; quem abre o segundo PR pode precisar clicar em **Update branch** no GitHub ou rodar `git merge origin/main` na própria branch.
- **Mesmo arquivo (ex.: `Sprints.md`):** pode ocorrer **conflito**. Resolver mantendo os status corretos das tasks (conversar na equipe). Mitigação: PRs pequenos, integração diária em `main`, ou combinar quem edita qual seção naquela semana.

### Tabela rápida

| Objetivo | Comando / ação |
| -------- | ---------------- |
| Ver o que já entrou no projeto | `git checkout main` → `git pull origin main` |
| Trazer `main` para minha branch | `git fetch origin` → `git merge origin/main` |
| Publicar meu trabalho para os outros | `push` + PR → merge em `main` |
| Conflito no `Sprints.md` | Abrir o arquivo, unificar linhas, `git add`, concluir merge |

---

## 4. Sequência de comandos — início de sessão (local)

Executar **nesta ordem** no diretório do repositório (PowerShell ou Git Bash). Ajuste `origin` se o remoto tiver outro nome.

```powershell
cd "C:\Users\<usuario>\Desktop\TCC_Calculadora_Acessivel"

git remote -v
git fetch origin
git status
git branch -vv
```

Atualizar a branch base:

```powershell
git checkout main
git pull origin main
```

Abrir ou criar branch de trabalho:

```powershell
# Já existe localmente
git checkout feature/minha-branch

# Criar nova a partir de main
git checkout -b feature/minha-branch
```

Se a branch já existe **só no remoto**:

```powershell
git checkout -b feature/minha-branch origin/feature/minha-branch
git pull
```

Conferir histórico recente:

```powershell
git log --oneline -15
```

Opcional — ver o que mudou em `main` desde o último merge na sua branch:

```powershell
git fetch origin
git log HEAD..origin/main --oneline
```

---

## 5. Sequência de comandos — fim de sessão (commit e envio)

```powershell
git status
git diff
git add -A
git commit -m "tipo: descrição curta em inglês"
git push -u origin HEAD
```

Mensagens de commit: seguir **[`.github/COMMIT_GUIDELINES.md`](../.github/COMMIT_GUIDELINES.md)** (Conventional Commits, inglês, escopo opcional). Exemplos rápidos: `docs: add GitHub workflow`, `feat(ui): scaffold calculator shell`.

Se for o **primeiro push** da branch:

```powershell
git push -u origin feature/minha-branch
```

No GitHub: abrir **Pull Request** de `feature/...` → `main`, descrever o que mudou e marcar revisor (outro membro da equipe).

---

## 6. Resolução rápida de conflitos (orientação)

Antes de continuar desenvolvendo após alguém ter integrado em `main`:

```powershell
git checkout feature/sua-branch
git fetch origin
git merge origin/main
# ou: git rebase origin/main (se a equipe preferir rebase linear)
```

Resolver conflitos nos arquivos indicados, depois `git add` e `git merge --continue` (ou `git rebase --continue`).

---

## 7. Checklist cognitivo (humano ou IA após comandos)

1. Ler [`PRD.md`](../PRD.md) (ou seções relevantes ao que será feito).
2. Ler [`Sprints.md`](../Sprints.md) — sprint e task atuais.
3. Ler [`docs/CONTEXT.md`](CONTEXT.md) — pendências da última sessão.
4. Consultar [`Cronograma/cronograma.md`](../Cronograma/cronograma.md) ou [`Cronograma/cronograma.html`](../Cronograma/cronograma.html) para marcos da semana; registo da equipa em [`docs/sessoes/`](sessoes/README.md).
5. Só então alterar código ou documentos; alinhar com a task escolhida.

---

## 8. GitHub (repositório remoto)

- **Issues** (opcional): uma issue por task grande, linkada ao item em `Sprints.md`.
- **Projects** (opcional): quadro Kanban espelhando sprints.
- **Pull Requests**: sempre que integrar trabalho significativo em `main`.
- **`.gitignore`**: manter atual (builds, binários, PDFs grandes se não forem versionados por política).

---

## 9. IA (Cursor) — uso dos prompts

Índice: [`Prompts/README.md`](../Prompts/README.md).

- **Abrir projeto / nova conversa**: colar ou anexar [`Prompts/bootstrap.txt`](../Prompts/bootstrap.txt) — Git (conforme permissões), leitura de artefatos, resumo **antes** de codar.
- **Encerrar trabalho**: [`Prompts/close-session.txt`](../Prompts/close-session.txt) — `Sprints.md`, `docs/CONTEXT.md`, handoff.
- **Sprint (cada sessão ou sob demanda)**: [`Prompts/agent-sprint-coach.txt`](../Prompts/agent-sprint-coach.txt) — avaliar se o sprint está saudável, alinhado ao cronograma e ao PRD; recomendações sem alterar arquivos até você pedir.
- **Semanal (ritual de liderança)**: [`Prompts/agent-weekly-squad-lead.txt`](../Prompts/agent-weekly-squad-lead.txt) — retrospectiva da semana, riscos, prioridades da próxima semana, checklist; útil como “tech lead / squad lead” assistido por IA.
- **Sincronização em equipe (`main` + branches)**: [`Prompts/agent-github-sync.txt`](../Prompts/agent-github-sync.txt) — a IA interpreta `fetch`/`status`/comparativo com `origin/main` e lembra o fluxo sequencial/paralelo da secção 3 deste documento.

Os prompts “agent-*” são **instruções fixas** (não rodam sozinhos): o comportamento depende do modelo e dos comandos que você autorizar no terminal.

---

## 10. Contato e decisões

Decisões de arquitetura ou mudança de escopo: registrar em `docs/CONTEXT.md` ou em comentário no PR, e refletir no `PRD.md` quando for requisito de produto.
