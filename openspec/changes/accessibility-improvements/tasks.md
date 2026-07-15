## 1. Exibição em notação convencional (expression-display)

- [ ] 1.1 Criar função de formatação token→símbolo (`√`, `π`, `x⁻¹`, `sen(`, `log_b(`) aplicada só na exibição, sem alterar `CalculatorState.expression`
- [ ] 1.2 Ligar a formatação ao `_update_display` do `ui_lcd/app.py`, preservando o truncamento
- [ ] 1.3 Garantir coerência rótulo/exibição/voz para cada símbolo
- [ ] 1.4 Teste unitário da formatação (entrada canônica → saída exibida) sem tocar no motor

## 2. Áudio: interrupção e cobertura (audio-feedback)

- [ ] 2.1 Revisar interrupção no `SpeechService` para corte determinístico (limpeza de fila + término confiável)
- [ ] 2.2 Medir latência do TTS no fluxo atual (processo por anúncio) e decidir se migra para motor persistente
- [ ] 2.3 Auditar todos os elementos interativos e garantir anúncio consistente (teclas, Ctrl/Shift, modo, histórico)
- [ ] 2.4 Conferir nomes falados de símbolos e a leitura do resultado exibido (pt-BR)
- [ ] 2.5 Remover/condicionar o logging de debug em arquivo no caminho de teclas (`speech_debug.log`)

## 3. Contraste e paleta (visual-accessibility)

- [ ] 3.1 Adicionar utilitário de razão de contraste (WCAG) para checar pares texto/fundo
- [ ] 3.2 Ajustar a paleta de botões/display para atingir WCAG AA (≥4,5:1 / ≥3:1 grande)
- [ ] 3.3 Garantir diferenciação de categorias por mais de um atributo além da cor
- [ ] 3.4 Verificar legibilidade da tipografia no 800x480 mantendo o truncamento seguro

## 4. Feedback de estado (interaction-feedback)

- [ ] 4.1 Indicação visual de foco/pressionado/selecionado nos botões
- [ ] 4.2 Retorno sonoro correspondente aos estados, reutilizando a fila do TTS
- [ ] 4.3 Refletir estado de Ctrl/Shift/modo simultaneamente em visual e áudio

## 5. Mensagens de erro (error-messaging)

- [ ] 5.1 Revisar textos de `ERROR_MESSAGES` para clareza, mantendo os códigos §13
- [ ] 5.2 Garantir coerência UI↔TTS por código e precedência de P1 sobre P2
- [ ] 5.3 Teste unitário do mapeamento código→mensagem

## 6. Navegação por teclado (keyboard-navigation)

- [ ] 6.1 Garantir operação completa por teclado (dígitos, operadores, funções, =, AC, DEL)
- [ ] 6.2 Configurar ordem de foco previsível (Tab/setas) com foco visível/anunciável
- [ ] 6.3 Avaliar e documentar atalhos adicionais no mapeamento de teclas

## 7. Repetir última resposta (recall-last-answer)

- [ ] 7.1 Guardar o último resultado completo (sem truncamento) no estado
- [ ] 7.2 Mapear Shift/Ctrl+`=` para reanunciar e reexibir a resposta completa sem recalcular
- [ ] 7.3 Tratar ausência de resposta anterior (coerente com WRN-010) sem alterar a expressão
- [ ] 7.4 Teste unitário do recall (com e sem resultado prévio; valor completo vs truncado)

## 8. Auditoria e validação (itens 1 e 8)

- [ ] 8.1 Registrar como pendência de decisão (orientador) os gaps de motor fora de escopo: botão `exp(` sem função; `polar`/`rect` incompletos
- [ ] 8.2 Rodar a suíte `python -m unittest discover -s software/tests -t .` e manter verde
- [ ] 8.3 Roteiro de teste de usabilidade com foco em acessibilidade e captura de achados
