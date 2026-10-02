# Contexto da última sessão (memória curta)

Atualizar no **encerramento** de cada sessão de trabalho (humano ou via prompt [`prompts/close-session.txt`](../../prompts/close-session.txt)).

---

- Implementação da função `logbase(base, value)` acionada por `Shift + log`. Atualização do motor de cálculo (`engine.py`), da interface LCD (`app.py`) e inclusão de testes unitários.

## Estado atual

- Repositório remoto ativo com a feature de logaritmo customizado (`logbase`) implementada e testada. Interface LCD agora suporta o estado `Shift` para o botão `log`.
- Documentação normativa: [`docs/produto/PRD.md`](../produto/PRD.md); tempo: [`cronograma/`](../../cronograma/); registo da equipa: [`sessoes/`](sessoes/README.md).
- Backlog: [`Sprints.md`](Sprints.md).

## Pendências / débitos
- Refatoração do botão de separador decimal (T1.6) para suportar Shift (vírgula).
- Combinar convenção de branches e revisão de PR (T1.3 em [`Sprints.md`](Sprints.md)).
- Manter `Sprints.md` e este `CONTEXT.md` atualizados por sessão (T1.2).

## Riscos / atenções
- Discussão com o professor Yuri em 18/05/2026 sobre os resultados e validação das novas funções.
- Prazo acadêmico: Entrega da Semana 12 em andamento.
- Existe um repositório Git em **`C:\Users\gusta`** (pasta do utilizador). Fora da pasta do projeto, comandos `git` podem afetar ficheiros errados. Trabalhar sempre com `cd` para `Desktop\TCC Calculadora` ou remover/renomear o `.git` da home se foi criado por engano.

## Próximo foco sugerido
- Concluir refatoração do botão de separador decimal (T1.6).

## Tasks concluídas nesta sessão
- [INTERNAL] Validação total do motor de cálculo via `test_arithmetic.py`.
- [NEW] Suporte a porcentagem (`%`) no engine.
