# Testes — resultados e roteiros

O que já foi **validado** e o que ainda precisa ser executado com pessoas. Os testes automatizados vivem em [`../../software/tests/`](../../software/tests/); esta pasta guarda os **registos** e os roteiros manuais.

| Documento | Tipo | Estado |
| --------- | ---- | ------ |
| [arithmetic_tests_2026-05-17.md](arithmetic_tests_2026-05-17.md) | Log de execução — aritmética e funções científicas (15 suítes, robustez e precisão) | Executado em **2026-05-17**: 15/15 sucesso |
| [testes_logaritmicos_renumerado.md](testes_logaritmicos_renumerado.md) | Casos esperados de logaritmos (55 casos: base, mudança de base, precisão, performance) | Conferido |
| [usability_test_script_accessibility.md](usability_test_script_accessibility.md) | **Roteiro** de usabilidade com foco em acessibilidade | **Pendente** — a executar com usuários reais |

## Convenções

- Relatório de execução leva **data no nome** (`*_AAAA-MM-DD.md`) — é um registo histórico, não se reescreve.
- Roteiro (documento a executar) **não** leva data: é reutilizado a cada rodada, e os achados de cada rodada entram na seção final.
- Achado que vira trabalho: abrir task em [../desenvolvimento/Sprints.md](../desenvolvimento/Sprints.md) ou proposta em [`../../openspec/changes/`](../../openspec/changes/).

## Relacionado

- Requisitos que estes testes verificam: [../produto/PRD.md](../produto/PRD.md) §5 (funções) e §13 (códigos de erro)
- Suíte automatizada: `make check`
