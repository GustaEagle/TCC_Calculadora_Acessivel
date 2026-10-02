# Produto — requisitos e definição

O que a calculadora **deve** ser. Esta pasta é a referência normativa: quando o código diverge daqui, ou o código está errado, ou o PRD precisa ser atualizado — não se resolve por decisão isolada.

| Documento | Conteúdo |
| --------- | -------- |
| [PRD.md](PRD.md) | **Documento de requisitos de produto** (v1.5): personas, requisitos funcionais (RF) e não funcionais (RNF), saídas de vídeo, catálogo de funções, códigos de erro, SO/arranque |
| [materiais-e-metodos-tcc.md](materiais-e-metodos-tcc.md) | **Materiais e métodos** do TCC: componentes de hardware, especificações e finalidade de cada peça no protótipo |

## Como se lê o PRD

- **RF-xx / RNF-xx** são os identificadores citados pelo backlog, pelas propostas em [`../../openspec/`](../../openspec/) e pelos comentários no código — cite sempre o identificador, não o número da seção.
- Mudança de escopo entra **primeiro** no PRD e no [cronograma](../../cronograma/cronograma.md), depois vira task em [../desenvolvimento/Sprints.md](../desenvolvimento/Sprints.md).

## Relacionado

- Comportamento já implementado do teclado: [../guias/comandos-teclado.md](../guias/comandos-teclado.md)
- O que foi validado contra os requisitos: [../testes/](../testes/README.md)
