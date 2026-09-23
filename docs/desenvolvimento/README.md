# Desenvolvimento — como a equipe trabalha

Processo, estado e memória do trabalho de **Gustavo, João e Yuri**. Nada aqui descreve o produto (isso é [../produto/](../produto/README.md)); tudo aqui descreve *como chegamos lá*.

| Documento | Quando se lê | Quando se escreve |
| --------- | ------------ | ----------------- |
| [CONTEXT.md](CONTEXT.md) | **Início** de sessão — onde a anterior parou, pendências, próximo foco | **Fim** de cada sessão |
| [Sprints.md](Sprints.md) | Ao escolher o que fazer — backlog por sprint, responsável e status | Ao concluir ou criar task |
| [GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md) | Antes de abrir branch ou PR — convenções de nome e sequência de comandos | Ao mudar a convenção da equipe |
| [REPO_STRUCTURE.md](REPO_STRUCTURE.md) | Ao não saber onde um ficheiro deve morar — mapa PRD → pastas | Ao criar área nova no repositório |
| [sessoes/](sessoes/README.md) | Para saber o que cada pessoa fez na semana N | **Fim** de cada sessão, no ficheiro `semana-NN.md` |

## Ciclo de uma sessão

1. **Abrir:** ler `CONTEXT.md` e a task em `doing` no `Sprints.md` (prompt: [`../../prompts/bootstrap.txt`](../../prompts/bootstrap.txt)).
2. **Trabalhar:** branch a partir de `main` atualizada, conforme `GITHUB_WORKFLOW.md`.
3. **Fechar:** atualizar `CONTEXT.md`, marcar o status no `Sprints.md` e registar em `sessoes/semana-NN.md` (prompt: [`../../prompts/close-session.txt`](../../prompts/close-session.txt)).

## Relacionado

- Prazos académicos: [`../../cronograma/cronograma.md`](../../cronograma/cronograma.md)
- Mensagens de commit: [`../../.github/COMMIT_GUIDELINES.md`](../../.github/COMMIT_GUIDELINES.md)
- Propostas de mudança em aberto: [`../../openspec/changes/`](../../openspec/changes/)
