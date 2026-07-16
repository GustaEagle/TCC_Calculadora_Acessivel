## Context

A calculadora acessível já tem núcleo (`core/`) desacoplado da UI, front em ttkbootstrap (`ui_lcd/app.py`) e TTS por `pyttsx3` (`accessibility/speech.py`). A revisão apontou lacunas de acessibilidade concentradas na **camada de apresentação e áudio**, não no motor. Este design cobre as 7 capacidades da proposta e mantém a regra do PRD §8: a UI consome estado, o `core/` não conhece a UI.

Estado atual relevante:
- A expressão é exibida com tokens crus (`sqrt(`, etc.) — a exibição usa diretamente o texto de `CalculatorState.expression`.
- A interrupção de fala inicia um `multiprocessing.Process` por anúncio e o encerra com `terminate()`; o comportamento é intermitente.
- As cores dos botões vêm de `_button_style` (mapeamento fixo de bootstyles), sem verificação de contraste.
- Mensagens de erro já existem em `ERROR_MESSAGES` e os códigos vêm do PRD §13.
- Há logging de debug em arquivo (`speech_debug.log`) em caminho quente.

## Goals / Non-Goals

**Goals:**
- Melhorar exibição, áudio, contraste, feedback de estado, mensagens, navegação por teclado e recall — tudo na camada de apresentação/áudio.
- Manter o `core/` intacto e independente de UI.
- Tornar cada melhoria testável (unit onde couber; roteiro manual para contraste/áudio).

**Non-Goals:**
- **Não** alterar o catálogo matemático do PRD §5 (ver "Auditoria" abaixo).
- **Não** implementar o front do monitor HDMI (`ui_hdmi/`) nesta mudança.
- **Não** introduzir novo botão físico para o recall (usa ação secundária do `=`).

## Decisions

### D1 — Camada de exibição separada do estado bruto
Introduzir uma função de formatação para apresentação (token canônico → símbolo convencional) aplicada **somente na exibição**, mantendo `CalculatorState.expression` com os tokens que o motor entende. **Por quê:** preserva o desacoplamento e evita reescrever o parser. *Alternativa descartada:* trocar os próprios tokens de entrada — quebraria a normalização do `engine`.

### D2 — Interrupção de fala mais determinística
Rever o mecanismo de interrupção do `SpeechService` para que o corte de anúncios de menor prioridade seja consistente (limpeza de fila + término confiável do que está tocando). Avaliar reduzir o custo de recriar processo/engine por anúncio. **Por quê:** o RF-08 exige que a entrada não fique bloqueada e o feedback crítico não atrase. *Alternativa considerada:* motor de TTS persistente com canal de comando — registrada como possível evolução.

### D3 — Contraste como critério objetivo (WCAG AA)
Adotar razão de contraste WCAG 2.1 AA como métrica verificável para o RF-12, com um pequeno utilitário de cálculo de contraste para checar os pares cor de texto/fundo usados. **Por quê:** transforma "melhor contraste" (subjetivo) em critério testável.

### D4 — Feedback de estado por dois canais
Padronizar foco/pressionado/selecionado com indicação visual e anúncio sonoro reutilizando a fila do `SpeechService`. **Por quê:** RF-04/RF-12 — não depender só da visão.

### D5 — Recall como ação secundária do `=`
Mapear Shift/Ctrl+`=` para reanunciar/reexibir o último resultado **completo** (guardado no estado, sem truncamento), sem recalcular. **Por quê:** atende o pedido sem novo botão e reaproveita `last_result`/histórico.

## Risks / Trade-offs

- **Recriar processo de TTS por anúncio custa latência no Pi** → medir; se necessário, migrar para motor persistente (D2 evolução).
- **Truncamento de exibição pode divergir do valor falado** → recall e leitura de resultado devem usar o valor completo, não o texto truncado.
- **Mudança de paleta pode conflitar com o tema `darkly`** → validar contraste após ajustes, não assumir que o tema já cumpre AA.
- **Navegação por foco no Tkinter** pode exigir configuração explícita de ordem de foco → tratar como tarefa dedicada.

## Auditoria (itens 1 e 8 — não viram spec)

Estes itens da lista original são **atividades de revisão**, não requisitos de comportamento, e ficam registrados aqui:

- **Item 1 — Revisar funcionalidades / recursos ausentes:** a análise de código já encontrou gaps reais no motor que tocam o catálogo §5 e por isso ficam **fora do escopo** desta mudança (exigem validação acadêmica no TCC):
  - Botão `exp(` existe na UI mas não há função `exp` no `engine` → avaliar ao aplicar (`ERR-007` enganoso hoje).
  - `polar`/`rect` retornam apenas uma componente do par (só x / só raio) → conversão incompleta vs §5.
  Ação: registrar como pendência para decisão do orientador antes de qualquer alteração no §5.
- **Item 8 — Testes de usabilidade com foco em acessibilidade:** conduzir sessão de teste com usuários (ou roteiro guiado) após implementar as specs; capturar achados e realimentar novas propostas. Não é implementável como código.

## Open Questions

- Motor de TTS persistente vs processo por anúncio: medir latência no Pi 4B antes de decidir.
- Qual atalho para o recall — Shift+`=` ou Ctrl+`=` — considerando os mapeamentos já existentes de Ctrl/Shift.
- Definir o conjunto mínimo de atalhos de teclado adicionais (item 11) com base no teste de usabilidade (item 8).
