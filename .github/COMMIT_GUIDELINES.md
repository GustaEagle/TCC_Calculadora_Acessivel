# Diretrizes de commit (TCC Calculadora)

Padronização de mensagens de commit para este repositório (equipe: Gustavo, João, Yuri).  
Base: [Conventional Commits](https://www.conventionalcommits.org/) (mesma ideia do guia “Service-Desk”, adaptada ao projeto).

---

## 1. Objetivo

- Manter histórico **legível** e fácil de bisectar (`git bisect`).
- Facilitar **revisão** em PR e, no futuro, **changelog** semi-automático.
- Alinhar comunicação entre hardware, firmware/software e documentação.

---

## 2. Formato

```
<tipo>[escopo opcional]: descrição curta em inglês
```

- **Título:** imperativo (“add”, “fix”, não “added” / “fixes”).
- **~72 caracteres** no título (recomendado).
- **Corpo (opcional):** linha em branco após o título; explicar *por quê*, listar pontos importantes, referenciar issue/PR.

Exemplo com corpo:

```text
feat(ui): add basic LCD layout shell

Wireframe only; behavior in follow-up PR.
Closes #12
```

---

## 3. Tipos (quando usar)

| Tipo | Uso neste projeto |
| ---- | ----------------- |
| `feat` | Nova funcionalidade ou melhoria visível (UI, cálculo, integração GPIO, fluxo da calculadora). |
| `fix` | Correção de bug ou falha de integração. |
| `docs` | README, `docs/`, PRD, comentários de documentação, diagramas. |
| `style` | Formatação, lint, imports — **sem** mudança de comportamento. |
| `refactor` | Reestruturação de código sem novo comportamento. |
| `perf` | Otimização de tempo, CPU ou memória. |
| `test` | Testes unitários, integração ou e2e. |
| `chore` | Manutenção geral: dependências, scripts, tarefas de housekeeping. |
| `build` | Build, empaquetamento, toolchain (ex.: scripts de release). |
| `ci` | Apenas pipelines (`.github/workflows`, etc.), sem mudar código de produto. |

---

## 4. Escopo (opcional, recomendado quando claro)

Ajuda em monorepos ou pastas grandes. Exemplos para este trabalho:

- `feat(calc):` — núcleo de expressões / precisão.
- `feat(ui):` / `feat(lcd):` — interface no painel.
- `fix(gpio):` — leitura de teclado / pinagem.
- `docs(pinout):` — `docs/raspberry-pi-4b/`.
- `docs(waveshare):` — notas UPS/LCD.
- `hardware(kicad):` ou `hardware(layout):` — PCB, esquemático, teclado.
- `chore(repo):` — `.gitignore`, prompts, organização de pastas.

Use escopo **curto** e consistente na equipe.

---

## 5. Fluxo rápido

```powershell
git checkout -b feature/descricao-curta
# ... alterações ...
git add -A
git commit -m "feat(ui): add display status placeholder" -m "Scaffold only; logic in next task."
git push -u origin feature/descricao-curta
```

Abrir **Pull Request** para `main`; referenciar issue, se existir (`Closes #n` no corpo).

---

## 6. Ajustes locais (com cuidado)

- `git commit --amend` — corrigir **última** mensagem ou incluir arquivos esquecidos (antes do push, ou com acordo da equipe se já publicado).
- `git reset --soft HEAD~1` — desfazer último commit mantendo alterações no stage/working tree.
- `git rebase -i HEAD~n` — reorganizar mensagens/commits **antes** de merge (alinhar com a equipe; evitar reescrever histórico compartilhado sem necessidade).

---

## 7. Regras fixas da equipe

1. Mensagens em **inglês** (título e, de preferência, corpo).
2. Um commit deve representar uma **unidade lógica** de mudança quando possível (facilita review).
3. Usar **escopo** quando deixar o contexto óbvio (`feat(lcd):`, `docs(workflow):`, etc.).

Documento irmão: [`docs/GITHUB_WORKFLOW.md`](../docs/GITHUB_WORKFLOW.md).
