## 1. DisplaySelector real (display-switching)

- [x] 1.1 Definir `HdmiPortReader` (protocolo/interface) em `software/hw_platform/display.py` com um método que informa se a saída HDMI do LCD e a do monitor externo estão reconhecidas.
- [x] 1.2 Criar um `HdmiPortReader` fake/simulado (para uso em desenvolvimento e testes), e deixar espaço para uma implementação real futura (fora de escopo desta mudança).
- [x] 1.3 Reescrever `DisplaySelector.__init__` para aceitar um `HdmiPortReader` injetável (default: fake) e `current_mode()` para implementar a prioridade do PRD §7.4 (monitor+LCD → `HDMI`; só LCD → `LCD`; nenhum → `AUDIO_ONLY`).
- [x] 1.4 Tratar o caso do interruptor físico do LCD desligado como "saída HDMI do LCD não reconhecida" na leitura do `HdmiPortReader`.
- [x] 1.5 Testes em `software/tests/` cobrindo as 3 combinações do fluxograma §7.4 (LCD+monitor, só LCD, nenhum) e o caso do interruptor desligado sem monitor.

## 2. Entrypoint único

- [x] 2.1 Criar `software/app.py` com `main()` que instancia `DisplaySelector`, consulta `current_mode()` e despacha para `ui_hdmi.app.CalculatorApp`, `ui_lcd.app.CalculatorApp`, ou um laço somente-áudio.
- [x] 2.2 Implementar o laço somente-áudio (RF-04): aceita teclado via `KeyboardAdapter`, processa tokens em `CalculatorState`, anuncia entradas/resultados via `SpeechService`, sem abrir janela ttkbootstrap.
- [x] 2.3 Adicionar uma flag opcional (`--force-mode lcd|hdmi|audio`) no entrypoint para forçar o modo manualmente em desenvolvimento/demonstração.
- [x] 2.4 Atualizar `README.md`/docs relevantes para apontar `software/app.py` como forma de executar a calculadora, mantendo `ui_lcd.app:main()` funcional para uso direto/testes locais.
- [x] 2.5 Teste em `software/tests/` garantindo que o entrypoint instancia exatamente um front (ou nenhum, no modo áudio) por modo retornado pelo `DisplaySelector`.

## 3. Front-end ui_hdmi (hdmi-ui)

- [x] 3.1 Criar `software/ui_hdmi/__init__.py` e o esqueleto de `software/ui_hdmi/app.py` com `CalculatorApp` (ttkbootstrap), importando `CalculatorState` de `software/core`, `SpeechService` de `software/accessibility`, e os adaptadores de `software/hw_platform`.
- [x] 3.2 Projetar o layout para tela maior e responsivo: sem `geometry`/`minsize` fixos como o LCD, usando `columnconfigure`/`rowconfigure` com `weight` para expressão, resultado, teclado e histórico se realocarem proporcionalmente à resolução real do monitor detectada na inicialização (design.md, decisões 1 e 2).
- [x] 3.2.1 Testar manualmente o layout em pelo menos duas resoluções/tamanhos de janela diferentes (ex.: 1920x1080 e 1366x768, ou redimensionamento manual no PC) e confirmar que nada é cortado, sobreposto ou fica desproporcional. — Verificado em 1920x1080, 1366x768, 1280x720 e 800x480: 0 widgets cortados/colapsados, fontes escalam (botão 25→18→17→10 pt). O gestor de janelas da máquina de dev recusa redimensionamento programático, por isso as resoluções foram simuladas na camada onde a app lê o tamanho da janela, e a matemática de escala ficou coberta por testes puros em `test_responsive_layout.py`.
- [x] 3.3 Reaproveitar/mover para local compartilhado o que for idêntico ao `ui_lcd` (ex.: `error_messages.py` — mapeamento de código PRD §13 → texto amigável) evitando duplicar texto de erro.
- [x] 3.4 Criar `palette.py`/`formatting.py` (ou reaproveitar os do `ui_lcd` se não houver motivo para divergir) mantendo a paleta WCOG AA já validada em `ui_lcd/contrast.py`.
- [x] 3.5 Implementar o mapeamento de teclado físico (`KeyboardAdapter`) e a lógica de tokens/Ctrl/Shift equivalente à do `ui_lcd/app.py`, adaptada ao novo layout.
- [x] 3.6 Garantir que erros de domínio no front HDMI usem o mesmo código e prefixo de prioridade (Erro/Aviso) do PRD §13 que o front do LCD usa para o mesmo erro.
- [x] 3.7 Testar manualmente o front-end HDMI (executando localmente com `software/app.py --force-mode hdmi`) cobrindo: entrada numérica, funções científicas, histórico, erro de domínio (ex.: divisão por zero) e leitura de voz. — `12+3=15`, `sqrt(81)=9`, `sen(30)=0.5` (DEG), `1/0` → `ERR-001` na tela e "Erro 001…" na voz; painel de histórico renderizou as entradas. Corrigido no processo: o rodapé mostrava "Saida visual: LCD" no front do monitor porque reconsultava o `DisplaySelector`.

## 4. Fechamento

- [x] 4.1 Rodar toda a suíte de testes (`software/tests/`) e confirmar que os testes existentes (27) continuam passando junto dos novos. — **83 testes passam.** Nota: a suíte já tinha **61** testes antes desta mudança (não 27 — o número na task estava desatualizado); os 22 novos cobrem `DisplaySelector`, despacho do entrypoint, modo somente áudio e layout responsivo.
- [x] 4.2 Revisar que `software/core/` não foi alterado e que nenhuma função matemática nova (PRD §5) ou código de erro novo (PRD §13) foi introduzido. — `git status` confirma `software/core/` e `PRD.md` intocados; o catálogo de erros foi apenas movido para `ui_common/error_messages.py` com conteúdo byte-idêntico.
