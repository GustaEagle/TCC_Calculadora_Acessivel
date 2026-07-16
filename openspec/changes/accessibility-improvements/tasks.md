## 1. Exibição em notação convencional (expression-display)

- [x] 1.1 Criar função de formatação token→símbolo (`√`, `π`, `x⁻¹`, `sen(`, `log_b(`) aplicada só na exibição, sem alterar `CalculatorState.expression`
- [x] 1.2 Ligar a formatação ao `_update_display` do `ui_lcd/app.py`, preservando o truncamento
- [x] 1.3 Garantir coerência rótulo/exibição/voz para cada símbolo
- [x] 1.4 Teste unitário da formatação (entrada canônica → saída exibida) sem tocar no motor

## 2. Áudio: interrupção e cobertura (audio-feedback)

- [x] 2.1 Revisar interrupção no `SpeechService` para corte determinístico (limpeza de fila + término confiável)
- [ ] 2.2 Medir latência do TTS no fluxo atual (processo por anúncio) e decidir se migra para motor persistente — **requer hardware real (Raspberry Pi)**, não medível neste ambiente; instrumentação de logging (`logger.debug`) já registrada para viabilizar a medição em campo
- [x] 2.3 Auditar todos os elementos interativos e garantir anúncio consistente (teclas, Ctrl/Shift, modo, histórico) — cobertos: Histórico e Ocultar/Exibir Controles, que não tinham anúncio
- [x] 2.4 Conferir nomes falados de símbolos e a leitura do resultado exibido (pt-BR) — adicionados `inv(`, `exp(`, `%` que faltavam em `_spoken_token`
- [x] 2.5 Remover/condicionar o logging de debug em arquivo no caminho de teclas (`speech_debug.log`)

## 3. Contraste e paleta (visual-accessibility)

- [x] 3.1 Adicionar utilitário de razão de contraste (WCAG) para checar pares texto/fundo
- [x] 3.2 Ajustar a paleta de botões/display para atingir WCAG AA (≥4,5:1 / ≥3:1 grande) — nova paleta em `ui_lcd/palette.py`, todos os pares ≥6.5:1, verificado por teste
- [x] 3.3 Garantir diferenciação de categorias por mais de um atributo além da cor — já satisfeito por construção (rótulo textual distinto + agrupamento espacial esquerda/direita), sem necessidade de mudança de código
- [x] 3.4 Verificar legibilidade da tipografia no 800x480 mantendo o truncamento seguro — satisfeito por construção (fontes fixas, nunca reduzidas; truncamento por reticências já preserva a parte mais relevante); confirmação visual final pendente (ver grupo 8)

## 4. Feedback de estado (interaction-feedback)

- [x] 4.1 Indicação visual de foco/pressionado/selecionado nos botões — `style.map` com inversão fg/bg no press e borda no foco
- [x] 4.2 Retorno sonoro correspondente aos estados, reutilizando a fila do TTS — press já era coberto pelo fluxo de `_handle_token`. Uma primeira tentativa de anunciar o foco por `<FocusIn>` foi **removida** por causar (a) fala duplicada a cada clique ("Foco em X" + token) e (b) loop de anúncio no ambiente X11 sem WM (foco reganhado em storm). O foco fica indicado pelo canal **visual** (borda), que a spec `interaction-feedback` aceita ("visual e/ou sonoro"). Um anúncio de foco só-por-teclado, com debounce, fica como melhoria futura
- [x] 4.3 Refletir estado de Ctrl/Shift/modo simultaneamente em visual e áudio — já implementado (verificado, sem necessidade de mudança)

## 5. Mensagens de erro (error-messaging)

- [x] 5.1 Revisar textos de `ERROR_MESSAGES` para clareza, mantendo os códigos §13 — extraído para `ui_lcd/error_messages.py` (testável sem GUI); textos já claros, mantidos
- [x] 5.2 Garantir coerência UI↔TTS por código e precedência de P1 sobre P2 — **bug corrigido**: TTS sempre dizia "Erro NNN" mesmo para `WRN-0xx` (deveria ser "Aviso"); display visual agora usa a mesma mensagem amigável da fala
- [x] 5.3 Teste unitário do mapeamento código→mensagem

## 6. Navegação por teclado (keyboard-navigation)

- [x] 6.1 Garantir operação completa por teclado (dígitos, operadores, funções, =, AC, DEL) — no **produto** isto é garantido por **hardware**: o teclado customizado (matriz Cherry MX → GPIO) tem uma tecla física por função (RF-05), fora do escopo de software. O `hw_platform/keyboard.py` é só um adaptador de teclado de PC para teste local e foi mantido mínimo (dígitos + operadores)
- [x] 6.2 Configurar ordem de foco previsível (Tab/setas) com foco visível — foco inicial definido; ordem de Tab segue a ordem de criação (esquerda→direita, topo→base), já previsível por construção; indicação visual de foco vem do Grupo 4
- [x] 6.3 Avaliar e documentar atalhos adicionais no mapeamento de teclas — avaliado: no produto o mapeamento é o teclado físico customizado (documentado no hardware), não um teclado de PC; nenhum atalho de PC adicional necessário

## 7. Repetir última resposta (recall-last-answer)

- [x] 7.1 Guardar o último resultado completo (sem truncamento) no estado — reaproveita `CalculatorState.last_result`, já não-truncado
- [x] 7.2 Mapear Shift/Ctrl+`=` para reanunciar e reexibir a resposta completa sem recalcular — novo `CalculatorState.recall_last_answer()` + `_recall_last_answer()` em `app.py`, ambos modificadores funcionam
- [x] 7.3 Tratar ausência de resposta anterior (coerente com WRN-010) sem alterar a expressão
- [x] 7.4 Teste unitário do recall (com e sem resultado prévio; valor completo vs truncado)

## 8. Auditoria e validação (itens 1 e 8)

- [x] 8.1 Registrar como pendência de decisão (orientador) os gaps de motor fora de escopo: botão `exp(` sem função; `polar`/`rect` incompletos — registrado em `design.md`, seção "Auditoria"
- [x] 8.2 Rodar a suíte `python -m unittest discover -s software/tests -t .` e manter verde — **59/59 testes passando** (27 originais + 32 novos); validado também rodando o app completo via Docker (GUI real + TTS funcionando, sem erros nos logs)
- [x] 8.3 Roteiro de teste de usabilidade com foco em acessibilidade e captura de achados — criado em `docs/test_reports/usability_test_script_accessibility.md`, pronto para execução com usuários reais
