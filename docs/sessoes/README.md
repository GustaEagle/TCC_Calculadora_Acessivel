# Registro de sessões (equipe)

Objetivo: ao **fim de cada sessão** de trabalho, cada pessoa **anota o que desenvolveu**; **uma vez por semana do plano** tudo fica reunido no **mesmo ficheiro**, visível para Gustavo, João e Yuri e versionado no Git.

---

## Convenção de ficheiros

- Um ficheiro por **Semana N** do [`Cronograma/cronograma.md`](../../Cronograma/cronograma.md) (domingo a sábado, semana 1 = 01/03–07/03/2026).
- Nome: **`semana-NN.md`** com `NN` de **01** a **30** (ex.: `semana-07.md`).
- Local: esta pasta `docs/sessoes/`.

Para saber **N** a partir da data de hoje: usar o [`Cronograma/cronograma.html`](../../Cronograma/cronograma.html) (indica “Semana N do plano”) ou contar a partir de 01/03/2026.

---

## Estrutura dentro de cada `semana-NN.md`

Cada ficheiro tem três secções fixas (**Gustavo**, **João**, **Yuri**). Em cada sessão, a pessoa **acrescenta** no fim da sua secção um bloco com data e conteúdo (não apagar registos antigos da mesma semana).

Modelo de bloco por sessão:

```markdown
#### AAAA-MM-DD — resumo curto (opcional)

- **Task / ID:** ex. T1.2, ou descrição livre se ainda sem ID.
- **Feito:** bullets objetivos (o que foi implementado, decidido ou documentado).
- **PR / branch:** opcional.
- **Bloqueios / próximo:** opcional.
```

---

## Fluxo recomendado

1. Durante a semana, cada um vai **acrescentando** blocos no `semana-NN.md` correto (pode ser no fim de sessão ou antes do push).
2. No **close-session** (prompt [`Prompts/close-session.txt`](../../Prompts/close-session.txt)), incluir atualização deste registo junto com `docs/CONTEXT.md` e `Sprints.md`.
3. Integrar em `main` com o resto do trabalho para os outros verem o histórico agregado.

---

## Ficheiros

| Ficheiro | Semana do plano (exemplo) |
| -------- | ------------------------- |
| [`_template-semana.md`](_template-semana.md) | Modelo vazio para copiar ao criar `semana-NN.md` novo |
| [`semana-07.md`](semana-07.md) | Semana 7 — 12/04 a 18/04/2026 (exemplo inicial) |

Crie `semana-08.md`, etc., quando entrar a semana seguinte (ou crie todos de uma vez a partir do template, se preferirem).
