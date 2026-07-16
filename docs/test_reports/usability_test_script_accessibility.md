# Roteiro de teste de usabilidade — acessibilidade

**Contexto:** change `accessibility-improvements` (`openspec/changes/accessibility-improvements/`).
**Objetivo:** validar com usuários reais o que a implementação e os testes automatizados não conseguem confirmar sozinhos — clareza do áudio, contraste percebido, navegação sem mouse e ausência de fricção nos fluxos.

Este documento é um roteiro a ser **executado pela equipe** com usuários reais (idealmente incluindo pessoas com cegueira total e com baixa visão, conforme as personas do [PRD.md](../../PRD.md) §4). Os achados devem ser registrados na seção final e realimentar novas propostas/specs.

---

## Perfil dos participantes sugeridos

- Ao menos 1 pessoa com cegueira total (uso apoiado só em áudio).
- Ao menos 1 pessoa com baixa visão (ex.: ~50%, conforme PRD §4).
- Opcional: 1 pessoa sem deficiência visual, para comparação de baseline.

## Ambiente

- Rodar via Docker local ([docker-compose.yml](../../docker-compose.yml)) ou diretamente com `python -m software.app`.
- Fones de ouvido disponíveis (uso previsto no PRD §7.3).

---

## Roteiro de tarefas

Para cada tarefa, observar: **tempo até concluir**, **erros/hesitações**, **se o áudio foi suficiente para concluir sem olhar a tela**.

1. **Operação básica:** calcular `12 + 8` e ouvir o resultado.
2. **Função científica:** calcular `√(64)` e conferir se o valor falado e exibido fazem sentido.
3. **Erro proposital:** tentar `10 / 0` — o aviso falado explica o problema? O texto na tela usa a mesma mensagem?
4. **Aviso (não passa de erro rígido):** pressionar `Ans` sem nenhum cálculo anterior — confirmar que é anunciado como "Aviso", não "Erro".
5. **Repetir última resposta:** após um cálculo, usar Shift+`=` (ou Ctrl+`=`) e confirmar que a resposta é reanunciada sem precisar recalcular.
6. **Navegação só por teclado:** repetir as tarefas 1–5 sem tocar no mouse, usando os atalhos documentados em `software/hw_platform/keyboard.py`.
7. **Modificadores:** ativar Shift e Ctrl e conferir se o estado é percebido (visual e sonoro) antes de pressionar a função.
8. **Histórico:** abrir o histórico de operações e confirmar que a abertura é anunciada.
9. **Alternância Graus/Radianos:** trocar o modo e confirmar o anúncio correspondente.
10. **Leitura geral da tela:** para o participante com baixa visão, perguntar se o contraste e o tamanho do texto são suficientes em uso normal (sem ampliação extra).

---

## Perguntas pós-teste

- O que você faria diferente se estivesse usando a calculadora sozinho(a), sem apoio?
- Alguma mensagem falada foi confusa ou longa demais?
- Algum botão ficou "sem resposta" (nem visual nem sonora) em algum momento?
- Você conseguiria operar a calculadora inteira sem tocar na tela/mouse?

---

## Achados (preencher após as sessões)

| Data | Participante (perfil) | Tarefa | Achado | Prioridade | Ação sugerida |
| ---- | --------------------- | ------ | ------ | ---------- | ------------- |
| _(pendente)_ | | | | | |

> Ao preencher esta tabela, considere abrir uma nova proposta OpenSpec (`/opsx:propose`) para achados que exigam mudança de comportamento, em vez de editar o change já arquivado.
