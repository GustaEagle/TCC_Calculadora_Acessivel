## Why

A revisão da calculadora identificou lacunas de **acessibilidade** e de consistência de interface que afetam diretamente o público-alvo (usuários com cegueira total ou baixa visão): expressões exibidas com nomes internos (`sqrt(` em vez de `√`), interrupção de fala instável, contraste de botões não verificado, cobertura de retorno sonoro incompleta e ausência de um jeito rápido de reouvir a última resposta. São ajustes que reforçam os requisitos de acessibilidade do PRD (RF-04, RF-07, RF-08, RF-12) sem alterar o catálogo matemático (§5).

## What Changes

- Exibir expressões em **notação convencional** (`√`, `π`, `x⁻¹`, funções sem o parêntese interno cru) mantendo o motor recebendo os tokens canônicos.
- Tornar a **interrupção da fala** determinística: um anúncio de maior prioridade deve cortar o anterior de forma consistente (hoje o mecanismo por processo separado falha de forma intermitente).
- Garantir **retorno sonoro consistente** para todos os elementos interativos (teclas, modificadores Ctrl/Shift, alternância de modo, histórico, navegação) e leitura correta de **resultado e símbolos** digitados.
- Estabelecer **contraste e paleta acessíveis** para botões e elementos, com critério verificável (WCAG) alinhado ao RF-12.
- Dar **feedback de estado dos elementos** (foco, pressionado, selecionado) por canal visual e/ou sonoro.
- Padronizar as **mensagens de erro/feedback** para linguagem clara e objetiva, preservando os códigos do PRD §13.
- Adicionar **repetição da última resposta completa** como ação secundária do botão `=` (Shift/Ctrl+`=`), sem novo botão físico.
- Cobrir **navegação por teclado** e avaliar **atalhos adicionais** para uso sem mouse.

## Capabilities

### New Capabilities
- `expression-display`: como a expressão em edição é apresentada ao usuário (símbolos convencionais) sem mudar os tokens enviados ao motor.
- `audio-feedback`: cobertura, conteúdo e política de interrupção do retorno por voz (teclas, símbolos, resultados).
- `visual-accessibility`: paleta, contraste e legibilidade dos elementos visuais para baixa visão.
- `interaction-feedback`: indicação de estado (foco, pressionado, selecionado) por canal visual e/ou sonoro.
- `error-messaging`: conteúdo e clareza das mensagens de erro/aviso na UI e no TTS, mantendo os códigos §13.
- `keyboard-navigation`: navegação e atalhos de teclado para operar sem depender do mouse.
- `recall-last-answer`: reouvir/reexibir a última resposta completa via ação secundária do `=`.

### Modified Capabilities
- (nenhuma — não existem specs em `openspec/specs/` ainda; todas as capacidades acima são novas)

## Impact

- **Código afetado:** principalmente [software/ui_lcd/app.py](../../../software/ui_lcd/app.py) (exibição, cores, estados, bindings, mensagens) e [software/accessibility/speech.py](../../../software/accessibility/speech.py) (interrupção). A camada `core/` **não** deve ser acoplada à UI.
- **Requisitos do PRD:** RF-04 (só áudio), RF-07/§13 (erros), RF-08 (fila/interrupção do TTS), RF-12 (contraste/legibilidade).
- **Testes:** novos testes unitários para a lógica de exibição, recall e mapeamento de mensagens; verificação manual de contraste e áudio.
- **Fora de escopo:** correções no catálogo matemático §5 (botão `exp(`, conversões `polar`/`rect` incompletas) — registradas apenas como **auditoria** no `design.md`, pois exigem validação acadêmica no TCC.
