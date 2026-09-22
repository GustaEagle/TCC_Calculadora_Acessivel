## Context

Hoje só existe `ui_lcd/app.py` (ttkbootstrap, janela fixa 800x480). `software/hw_platform/display.py` define `DisplaySelector.current_mode()` como stub — sempre retorna `DisplayMode.LCD`. Não há entrypoint único: quem quiser rodar a calculadora chama `ui_lcd.app:main()` diretamente. PRD §7 exige que, quando o monitor externo HDMI é reconhecido, ele vire a saída visual **preferencial** e o LCD não replique a UI principal; sem monitor, cai para o LCD; sem nenhum vídeo utilizável, cai para modo somente áudio (RF-04).

Por ora a equipe optou por manter **dois pacotes de UI separados** (`ui_lcd/` e `ui_hdmi/`), cada um responsivo ao seu próprio espaço de tela — a unificação em uma única UI compartilhada foi considerada, mas fica adiada para uma mudança futura.

## Goals / Non-Goals

**Goals:**
- Front-end `ui_hdmi/` funcional para tela maior (layout, tipografia e área de histórico redesenhados — não um `ui_lcd` esticado).
- Janela do `ui_hdmi` responsiva à resolução real do monitor conectado (sem tamanho-alvo fixo tipo 1920x1080), usando grid/weight dinâmico do ttkbootstrap.
- `DisplaySelector` real, testável, que decide entre `LCD`, `HDMI` e `AUDIO_ONLY` seguindo o fluxograma do PRD §7.4.
- Um entrypoint (`software/app.py`) que consulta o `DisplaySelector` e instancia o front correto (ou roda em modo somente áudio).
- `core/` e `accessibility/speech.py` permanecem inalterados e compartilhados pelos dois fronts.

**Non-Goals:**
- Detecção real de hardware via `xrandr`/`tvservice`/DRM no Raspberry Pi em produção — fica isolada atrás de uma interface substituível/mockável, como os demais adaptadores de `hw_platform/` (o projeto roda hoje simulado no PC).
- Hot-swap dinâmico da UI enquanto o app está rodando (trocar o monitor com o processo já em execução) — a decisão de saída é tomada na inicialização; troca em tempo real fica como trabalho futuro (registrado em Open Questions).
- Qualquer mudança no motor de cálculo (`core/`), no catálogo de erros (PRD §13) ou no escopo matemático (PRD §5).
- Comportamento elétrico do interruptor físico do LCD (hardware) — o software só reage a "vídeo utilizável no LCD: sim/não".
- Unificar `ui_lcd/` e `ui_hdmi/` em uma única implementação de UI — considerado e adiado para uma mudança futura (ver Open Questions).

## Decisions

**1. `ui_hdmi/` é um pacote-irmão de `ui_lcd/`, não uma extensão dele.**
Ambos importam `core.CalculatorState`, `accessibility.speech.SpeechService` e os adaptadores de `hw_platform/`. `ui_hdmi/app.py` terá sua própria `palette.py`/`formatting.py`/`error_messages.py` quando o layout maior exigir (ex.: mais linhas de histórico visíveis, fontes proporcionalmente menores que as do LCD). Reaproveitar por importação direta dos módulos do LCD quando o conteúdo for idêntico (ex.: `error_messages.py`, que só mapeia código PRD §13 → texto, é candidato a mover para um local compartilhado em vez de duplicar).
- Alternativa descartada por ora: unificar os dois em uma única UI compartilhada — considerada, mas a equipe decidiu manter os pacotes separados por enquanto; fica registrada como direção possível para uma mudança futura.

**2. Layout do `ui_hdmi` é responsivo, não fixo em uma resolução-alvo.**
A janela usa `columnconfigure`/`rowconfigure` com `weight` (como já faz `ui_lcd/app.py` internamente) para que expressão, resultado, teclado e histórico se realocam proporcionalmente ao tamanho real reportado pelo SO na inicialização — sem herdar o `geometry("800x480")`/`minsize(800, 480)` fixos do LCD. Cobre tanto monitores diferentes (ex.: 1920x1080 vs. 1366x768) quanto redimensionamento manual da janela durante desenvolvimento/testes no PC.
- Alternativa descartada: fixar uma resolução-alvo única (ex.: sempre 1920x1080) — mais simples, mas quebraria em monitores com resolução menor/maior e não atende ao PRD §8 ("maior área, layout mais rico") de forma geral.
- Alternativa descartada: fullscreen com geometria fixada só na inicialização (sem recalcular ao redimensionar) — insuficiente para testes locais no PC, onde a janela é redimensionada manualmente com frequência.

**3. `DisplaySelector` recebe um `HdmiPortReader` injetável.**
`DisplaySelector.__init__(self, port_reader: HdmiPortReader | None = None)`. Em testes, um fake `HdmiPortReader` simula as combinações do §7.4. Em produção (fora de escopo desta mudança), uma implementação real consultaria o SO. Isso mantém `hw_platform/` consistente com `keyboard.py`/`ups.py`, que já isolam hardware atrás de adaptadores simulados.
- Alternativa descartada: variável de ambiente/flag de configuração fixa — insuficiente porque RF-02 exige reagir à presença real de cada saída, não a uma escolha estática.

**4. Prioridade de decisão implementa exatamente o fluxograma do PRD §7.4** (`both HDMI reconhecidos → só monitor`; `só LCD HDMI → só LCD`; `nenhum → sem vídeo/AUDIO_ONLY`), com o áudio sempre ativo em paralelo (§7.3) independente do resultado.

**5. Entrypoint único `software/app.py`** substitui a chamada direta a `ui_lcd.app:main()`: lê `DisplaySelector().current_mode()` e despacha para `ui_hdmi.app.CalculatorApp`, `ui_lcd.app.CalculatorApp`, ou um laço somente-áudio (RF-04) que aceita teclado e responde por TTS sem janela gráfica visível.

## Risks / Trade-offs

- [Duplicação de código entre `ui_lcd/app.py` e `ui_hdmi/app.py` (ambos grandes arquivos ttkbootstrap com layout de teclado similar)] → Mitigar extraindo, quando o segundo front deixar o padrão claro, um módulo comum de mapeamento de teclas/handlers de token (`_handle_token`) que os dois fronts chamam — mas não forçar essa extração nesta mudança para não bloquear a entrega do HDMI atrás de uma refatoração maior. Se no futuro a equipe decidir unificar os fronts (Open Questions), essa extração vira o primeiro passo natural.
- [Sem hardware real disponível para testar detecção HDMI de fato] → `HdmiPortReader` fica com fake determinístico em testes; a integração real com o SO fica registrada como item em aberto, alinhado ao que o PRD já assume ("detecção depende de SO e driver... itens em aberto até testes no hardware").
- [Modo somente áudio sem UI visível pode ser difícil de depurar/demonstrar em banca] → manter um `--force-mode` opcional de linha de comando no entrypoint para forçar LCD/HDMI/áudio manualmente durante desenvolvimento e demonstrações.

## Open Questions

- Unificar `ui_lcd/` e `ui_hdmi/` em uma única UI compartilhada (mesmo visual e comportamento nas duas saídas, só variando o tamanho renderizado) foi discutido e fica como candidato forte para uma mudança futura — não implementado aqui porque a equipe pediu para manter os dois fronts separados por enquanto.
- Troca de saída em tempo real (usuário conecta/desconecta o monitor com o app já aberto) fica para uma mudança futura, ou entra nesta? Assumido aqui: **fica para depois** — RF-02 fala em "alternar automaticamente" mas a "política de debounce e detecção a especificar" é explicitamente deixada em aberto pelo próprio PRD.
- Qual mecanismo real de detecção HDMI usar no Raspberry Pi (parsing de `tvservice`/`xrandr`/`/sys/class/drm`)? Fica como item em aberto, igual o PRD já sinaliza.
