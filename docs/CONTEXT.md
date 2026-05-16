# Contexto da última sessão (memória curta)

Atualizar no **encerramento** de cada sessão de trabalho (humano ou via prompt [`Prompts/close-session.txt`](../Prompts/close-session.txt)).

---

- Implementação da função `logbase(base, value)` acionada por `Shift + log`. Atualização do motor de cálculo (`engine.py`), da interface LCD (`app.py`) e inclusão de testes unitários.

## Estado atual

- Repositório remoto ativo com a feature de logaritmo customizado (`logbase`) implementada e testada. Interface LCD agora suporta o estado `Shift` para o botão `log`.
- Documentação normativa: `PRD.md`; tempo: `cronograma/cronograma.md` e `cronograma/cronograma.html`; registo da equipa: `docs/sessoes/`.
- Backlog: `Sprints.md`.

## Pendências / débitos

- Combinar convenção de branches e revisão de PR (T1.3 em `Sprints.md`).
- Manter `Sprints.md` e este `CONTEXT.md` atualizados por sessão (T1.2).

## Riscos / atenções

- Existe um repositório Git em **`C:\Users\gusta`** (pasta do utilizador). Fora da pasta do projeto, comandos `git` podem afetar ficheiros errados. Trabalhar sempre com `cd` para `Desktop\TCC Calculadora` ou remover/renomear o `.git` da home se foi criado por engano.

## Próximo foco sugerido

- Fechar Sprint 1 (T1.2, T1.3) e iniciar entregáveis de software/hardware alinhados ao PRD e ao cronograma.

## Tasks concluídas nesta sessão

- T1.5: Implementar logaritmo com base variável (Shift + log).
