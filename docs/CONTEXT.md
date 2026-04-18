# Contexto da última sessão (memória curta)

Atualizar no **encerramento** de cada sessão de trabalho (humano ou via prompt [`Prompts/close-session.txt`](../Prompts/close-session.txt)).

---

## Última ação

- `git init` na raiz do projeto (pasta **TCC Calculadora**), `origin` → `https://github.com/GustaEagle/TCC_Calculadora_Acessivel`, primeiro push em `main` (merge com o `README.md` criado no GitHub). Pasta local `bootfoverlay/` excluída do Git via `.gitignore` (cópia de firmware/boot, ~73 MB).

## Estado atual

- Repositório remoto ativo: **main** em GitHub com PRD, cronograma, docs, esqueleto `software/` / `system/`, KiCad em `hardware/pcb/`.
- Documentação normativa: `PRD.md`; tempo: `cronograma/cronograma.md` e `cronograma/cronograma.html`; registo da equipa: `docs/sessoes/`.
- Backlog: `Sprints.md`.

## Pendências / débitos

- Combinar convenção de branches e revisão de PR (T1.3 em `Sprints.md`).
- Manter `Sprints.md` e este `CONTEXT.md` atualizados por sessão (T1.2).
- Realizar **commit** do novo arquivo `materiais_e_metodos_tcc.md` no repositório.

## Riscos / atenções

- Existe um repositório Git em **`C:\Users\gusta`** (pasta do utilizador). Fora da pasta do projeto, comandos `git` podem afetar ficheiros errados. Trabalhar sempre com `cd` para `Desktop\TCC Calculadora` ou remover/renomear o `.git` da home se foi criado por engano.
- Há ficheiros alterados localmente pendentes de commit (ex: `materiais_e_metodos_tcc.md`).

## Próximo foco sugerido

- Realizar o stage (`git add`) e o commit do novo arquivo de Materiais e Métodos.
- Fechar as outras tarefas da Sprint 1 (T1.2, T1.3) seguindo o fluxo de branches acordado pela equipe.

## Tasks concluídas na última sessão

- Extração e documentação de componentes do prompt para `materiais_e_metodos_tcc.md` (Task T1.4).
- Primeiro commit e push para GitHub; repositório Git correto na pasta do projeto.
