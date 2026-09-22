## Context

A motivação está no `proposal.md` (seção Why) e os requisitos em `specs/keypad-matrix/spec.md`.

O que já existe e condiciona a abordagem:

- **`hw_platform/keypad_pinout.py`** é o lugar único onde nets viram pinos. Ele valida a pinagem na importação (GPIO repetido, pino físico errado) e é lido pela ferramenta de bring-up, pelos testes e, indiretamente, pelo `pinout.md` (o teste `PinoutDocumentationTest` compara as tabelas do markdown com o módulo). Hoje usa rótulos 1-based (`L1..L6`, `C1..C7`) ao lado das nets 0-based.
- **`tools/keypad_bringup.py`** tem três backends (`lgpio`, `gpiod` v2 e `RPi.GPIO`), todos só com `input_pullup`/`output_low`/`output_high`. Ele varre os 13 condutores nos dois sentidos porque a orientação dos diodos era desconhecida. O backend `gpiod` já descobriu uma particularidade da API v2 e reconfigura **todas** as linhas a cada troca.
- **`hw_platform/keyboard.py`** é só o adaptador do teclado de PC (`map_key(char)`). Os dois fronts ligam `<Key>`, `<Return>`, `<Escape>`, `<Control_*>` e `<Shift_*>` e chamam `_handle_token(primary, secondary, shifted)`. Vindas do teclado, só `Ans` e `AC` recebem a função secundária (preenchida à força). As demais secundárias só existem nos botões da tela.
- **`ui/shared/video_watch.py`** é o padrão de "trabalho periódico dentro do laço Tk": `root.after(interval, tick)`, testável com uma raiz falsa.
- **`app.py:run_mode()`** constrói `CalculatorState`, `SpeechService` e `VideoBlackout` **uma vez** e passa-os a cada front construído no laço do RF-09.
- **Imagem Alpine:** `py3-libgpiod` 2.2.4 (API v2), grupo `gpio` e regra `99-gpio.rules` (`/dev/gpiochip*` em `0660 root:gpio`). O prompt de hardware cita Raspberry Pi OS 13, que também traz `python3-libgpiod` 2.x. A API usada aqui é comum às duas.
- **PCB (`hardware/pcb/TCC-09-05-2026/*.kicad_pcb`):** a conferência das nets dos pads mostra que `SW(n+1)` ligado a `Colc` e, pelo diodo `D(n+1)`, a `Rowr` corresponde exatamente ao `SWn = CcLr` do mapa validado, incluindo as 4 posições vazias. O pad do switch que não vai à coluna liga ao **anodo** do diodo (`Net-(Dn-A)`), portanto a corrente vai da coluna à linha. Isso é coerente com coluna em HIGH e linhas com pull-down.

## Goals / Non-Goals

**Goals:**
- Um scanner correto por construção: as invariantes elétricas (uma coluna em saída, nenhuma linha em saída, restauração garantida) ficam num único lugar pequeno e testado.
- Lógica de varredura e de debounce testável sem hardware nem `gpiod`, rodando no CI (Python 3.11).
- Entrada da matriz pelo **mesmo** `_handle_token()` dos fronts, sem segundo caminho de tratamento de teclas.
- Nenhuma dependência nova. O PC e o CI continuam a funcionar sem `gpiod`.

**Non-Goals:**
- Matriz no modo somente áudio (ver Riscos: limitação conhecida).
- Função para a tecla `?`.
- Leitura orientada a interrupção (`edge events`). Ver D4.
- Suporte a outros SBCs.

## Decisions

### D1 — Rótulos 0-based: o rótulo de chicote é a net

Os rótulos `L1..L6`/`C1..C7` somem, e `MatrixLine.name` passa a ser `L0..L5`/`C0..C6`. Esse nome é igual à net do KiCad e à coordenada `C#L#` do mapa validado. O campo `net` continua existindo (`Row0`, `Col0`) para quem abre o esquemático.

*Alternativa rejeitada:* manter 1-based no chicote. O mapa validado, a coordenada dos eventos e o KiCad são todos 0-based. Manter duas numerações foi exatamente o que permitiu a troca `Row0`↔`Row2` passar despercebida.

### D2 — Mapa de switches em `keypad_pinout.py`, keycap como fato de hardware

`keypad_pinout.py` ganha `MatrixSwitch(switch: "SW9", col: 3, row: 1, keycap: "7")` e `SWITCHES` (38 entradas, na ordem `SW0..SW37`), além de `EMPTY_COORDS = {(2,1), (2,2), (2,3), (4,4)}` e de `switch_at(col, row) -> MatrixSwitch | None`. O keycap é o **texto impresso na tecla** (`Pol`, `x!`, `Pi`, `(`, `)`, `%`, `e`, `sen`, `cos`, `7`…`9`, `/`, `tan`, `log`, `4`…`6`, `*`, `x^-1`, `^`, `1`…`3`, `-`, `?`, `nCr`, `√`, `0`, `,`, `+`, `Ctrl`, `exp`, `Shift`, `Ans`, `=`, `AC`, `Del`). Isso é hardware, não token de software. A `_validate()` existente passa a checar também 38 switches, coordenadas únicas e dentro da grade, nenhuma sobre posição vazia e `SW#` sequencial.

A tradução keycap → token fica em `ui/shared/keypad.py` (D6), porque é decisão de software. Um docstring registra a correspondência `SWn` aqui = `SW(n+1)` no KiCad.

### D3 — Scanner em três camadas: IO, varredura/debounce puros e thread

Novo `software/hw_platform/keypad_matrix.py`:

1. **`MatrixIO` (protocolo):** `drive_column(bcm)`, `float_column(bcm)`, `read_rows() -> tuple[bool, ...]`, `float_all()` e `close()`.
   - **`GpiodMatrixIO`** é a única classe que importa `gpiod`, e o faz tardiamente dentro de `__init__`. Ela:
     - abre `/dev/gpiochip0` e confere `chip.get_info().label` (esperado `pinctrl-bcm2711`) e `get_line_info(offset).used` para as 13 linhas;
     - faz um único `gpiod.request_lines(..., consumer="calculadora-teclado", config=...)`;
     - lê as linhas com `request.get_values(ROW_BCM_PINS)` numa só chamada;
     - rastreia a coluna ativa e **recusa** (`RuntimeError`) ativar uma segunda coluna antes de flutuar a primeira. A invariante é imposta no nível mais baixo, não só por disciplina do chamador.
2. **Funções puras:**
   - `scan_once(io, settle_s, sleep) -> frozenset[tuple[int, int]]` percorre as colunas com `try: drive; sleep(settle); read finally: float`.
   - `Debouncer(debounce_s)` é uma máquina de estados por coordenada (estado confirmado, estado candidato e instante da última mudança). `update(now, closed) -> list[KeyEvent]` recebe o relógio **injetado** (`time.monotonic` em produção) para que os testes simulem ressalto sem dormir.
   - `KeyEvent` é um `dataclass(frozen)` com `keycap`, `coord` (`"C3L1"`), `switch` (`"SW9"`), `pressed: bool`, `col_bcm`, `row_bcm` e `timestamp`, mais `state` (`"pressionado"`/`"solto"`) derivado.
   - Coordenada vazia fechada gera um `logger.warning` uma vez por ocorrência e nenhum evento.
3. **`MatrixKeyboard`:** thread daemon que repete `scan_once` → `Debouncer.update` → entrega, com um pequeno intervalo entre varreduras (padrão de 2 ms). Expõe `open()` (classmethod que devolve `None` e loga quando a matriz não está disponível), `attach(sink)`/`detach()` e `close()`. `close()` sinaliza a parada, espera a thread (`join` com timeout), chama `io.float_all()` e depois `io.close()`, cada passo em `try/finally`. Uma exceção de IO na thread é logada, faz `float_all()` e **encerra** a thread, em vez de repetir em laço apertado.

*Alternativa rejeitada:* uma classe única com `gpiod` e lógica juntos, como no bring-up atual. Sem a costura, nada disto se testa no CI.

### D4 — Varredura por sondagem, não por eventos de borda

Com as colunas flutuando, as linhas não mudam quando uma tecla fecha. A borda só aparece com uma coluna ativa, então `gpiomon` (usado no diagnóstico) não serve para varrer a matriz. Uma varredura custa 7 × (2 reconfigurações + 1 leitura + ~1 ms) ≈ 8–9 ms. Com a pausa de 2 ms, isso dá ~100 varreduras/s: 5 ou mais amostras dentro da janela de 20 ms de debounce e latência bem abaixo dos ~500 ms do RNF-01.

### D5 — Toda reconfiguração descreve as 13 linhas

`GpiodMatrixIO._apply(active_col)` monta **sempre** o dicionário completo: `ROW_INPUT` para as 6 linhas, `COLUMN_HIGH` para a coluna ativa (se houver) e `FLOATING` para as demais. Esse dicionário vai para `request.reconfigure_lines()`.

O motivo é que a API C da libgpiod 2.x documenta que a nova configuração **substitui por completo** a anterior, e que linhas sem configuração explícita recebem o padrão da requisição. O ioctl `GPIO_V2_LINE_SET_CONFIG` do kernel também se aplica ao conjunto inteiro. O que os bindings Python fazem com as linhas omitidas não é algo em que se deva apoiar entre versões 2.x. Se uma linha omitida caísse no padrão (entrada sem bias), ela perderia o pull-down em silêncio e flutuaria, gerando teclas fantasma. O backend `gpiod` do bring-up atual já evitava isso da mesma forma, e um teste com `gpiod` falso exige as 13 linhas em cada chamada.

As três `LineSettings` são as do prompt de hardware: `FLOATING` (`INPUT`, `Bias.DISABLED`), `ROW_INPUT` (`INPUT`, `Bias.PULL_DOWN`) e `COLUMN_HIGH` (`OUTPUT`, `Bias.DISABLED`, `output_value=Value.ACTIVE`). A sequência por coluna é config(coluna HIGH) → leitura → config(todas flutuando). A passagem direta de `Cn` para `Cn+1` num só ioctl é proibida, porque o kernel não garante a ordem dentro de um ioctl.

### D6 — Keycap → entrada do catálogo em `keypad.py`

`ui/shared/keypad.py` ganha `entry_for_keycap(keycap) -> tuple[primary, secondary, shifted] | None`. A busca é feita pelo rótulo nas `LEFT_BUTTONS`/`RIGHT_BUTTONS` já existentes, com um dicionário explícito de aliases para os rótulos que diferem entre tecla e tela: `x^-1`→`x⁻¹`, `Del`→`DEL`, `,`→`.`.

O keycap `,` resolve para a entrada `.` (primária `.`, `Shift` → `,`). O motor usa `.` como separador decimal e `,` como separador de argumentos (`nCr(5,2)`), e essa é a semântica que a tecla já tem na tela. Um teste percorre os 38 switches e exige entrada para todos exceto `?`.

`?` devolve `None`. `keypad.py` ganha `NO_FUNCTION_SPEECH = "Tecla sem função"`, e o comentário de `LEFT_BUTTONS` que diz que a `?` "não existe na matriz" passa a dizer que ela existe e não tem função. O botão na tela continua vazio, porque a UI mostra o catálogo de operações, não o hardware.

### D7 — Ponte fila → Tk compartilhada (`ui/shared/matrix_input.py`)

`MatrixInputPump(root, keyboard, on_press, on_unmapped, interval_ms=10)`:

- `start()` faz `keyboard.attach(queue.put_nowait)` e agenda `tick`;
- `tick()` drena a `queue.Queue`, ignora solturas, resolve o keycap por `entry_for_keycap` e chama `on_press(primary, secondary, shifted)` (o `_handle_token` do front) ou `on_unmapped(event)`, e reagenda;
- `stop()` faz `detach()`.

Tudo o que toca Tk roda no laço Tk. A thread só faz `put_nowait`. É o mesmo formato do `VideoOutputWatch`, testável com uma `FakeRoot`.

Os fronts recebem `keypad_matrix: MatrixKeyboard | None = None` no construtor, como `blackout`, e criam o pump se ele não for `None`. O `stop()` é chamado quando a janela é destruída (entrega do RF-09 ou saída). Um `attach` substitui o sink anterior. O `Debouncer` continua rodando entre fronts, então uma tecla segurada durante a troca não gera pressionamento duplicado. Eventos sem sink são descartados, e nada acumula durante o arranque do front seguinte.

*Alternativa rejeitada:* `root.event_generate("<<Matrix>>")` a partir da thread. O Tk não é thread-safe, e em Tcl sem threads isso trava de forma intermitente.

### D8 — Posse no `run_mode()` e encerramento limpo

- `app.py` ganha `--keypad-matrix {auto,off}` (padrão `auto`).
- `run_mode()` chama `MatrixKeyboard.open()` uma vez, passa o resultado a `start_front()` → front e fecha-o no `finally`.
- O modo somente áudio **não** recebe o scanner (Non-Goal). O scanner fica aberto, sem sink, e volta a ser usado se o vídeo voltar.
- `main()` instala handlers de `SIGTERM` e `SIGHUP` que levantam `SystemExit`, para que o `finally` rode quando o `.xinitrc` ou a sessão encerrarem o app. `SIGINT` já vira `KeyboardInterrupt`.
- O Tk só devolve o controle ao Python entre callbacks, mas o `tick` de 10 ms do pump garante que o handler rode logo.
- `open()` em `auto` devolve `None` com `logger.info` quando não há `gpiod` ou `/dev/gpiochip0` (PC/CI). Com `logger.warning` quando o chip existe mas a abertura falha (permissão, linha ocupada, chip errado), porque no Pi isso é defeito de instalação.

### D9 — Ferramenta de bring-up sobre o scanner

`tools/keypad_bringup.py` passa a importar `GpiodMatrixIO`, `scan_once`, `Debouncer` e `SWITCHES`:

- **modo padrão:** imprime cada evento com todos os campos (`pressionado  SW9  C3L1  "7"  coluna GPIO21  linha GPIO9`) e, no `Ctrl+C`, a grade 7x6 com os switches vistos (`38` esperados, posições vazias marcadas);
- **`--list`:** imprime condutores e mapa de switches sem tocar no hardware;
- **`--toggle C3|L0`:** pisca **um** condutor entre 0 V e 3,3 V com todos os outros em entrada sem bias. É uma única saída, então não existe par de saídas com níveis opostos;
- opções `--settle-ms` (padrão 1) e `--debounce-ms` (padrão 20).

Saem os backends `lgpio` e `RPi.GPIO`, a varredura bidirecional com pull-up e o relatório de sentido dos diodos. O sentido já está confirmado, e manter uma segunda polaridade no repositório contradiz a instrução de hardware.

## Risks / Trade-offs

- **[Coluna presa em HIGH se o processo morrer]** → Há três camadas: `try/finally` por coluna, `close()` com `float_all()` e handlers de `SIGTERM`/`SIGHUP`. Num `SIGKILL` nada roda, e o kernel libera a requisição ao fechar o descritor. O driver `pinctrl-bcm2835` devolve o pino a entrada ao liberá-lo, mas isso **não** é premissa do design: fica como item de conferência com `pinctrl get 9-11,13-15,17,19-22,26-27` após `kill -9` no bring-up. Mesmo em HIGH, a coluna só alimenta linhas com pull-down através de diodos, sem curto.
- **[UART0/SPI0 reativados por engano]** → GPIO14/15 (C6/C5) e GPIO9–11 (L1/L2/L0) morrem em silêncio se `enable_uart=1` ou `dtparam=spi=on`. A checagem de `line_info.used` pega o caso em que um driver requisitou a linha. Se não pegar, `pinout.md` §6.3 já documenta a condição.
- **[Custo de CPU da sondagem]** → ~14 ioctls e ~7 leituras por varredura, a ~100 Hz. É desprezível no Pi 4, e as constantes de intervalo e estabilização ficam configuráveis.
- **[Limitação conhecida: modo somente áudio sem matriz]** → Com o interruptor do LCD desligado e sem monitor, o app cai para `AUDIO_ONLY`, que lê o `stdin`. No produto sem teclado USB, isso fica sem entrada. O modelo de uso incentivado para o utilizador cego é o blackout (`Ctrl` + `AC`), que mantém o front ativo e portanto a matriz. Registrar como mudança seguinte: extrair a máquina de teclas dos fronts para `ui/shared` e ligá-la ao `AudioOnlyCalculator`.
- **[Mudança de rótulos quebra referências antigas]** → `L1..L6`/`C1..C7` aparecem em `pinout.md`, no bring-up e nos testes, todos atualizados nesta mudança. O `grep` de `"L6"`/`"C7"` faz parte das tarefas.

## Migration Plan

Não há dados nem estado persistido. Com o novo código, a bancada passa a usar os rótulos 0-based. A tabela de cores do `pinout.md` é a referência. Rollback: reverter o commit. Sem matriz, o app volta ao comportamento atual (só teclado de PC).

## Open Questions

- **Função da tecla `?`**: o design só a reconhece e anuncia "Tecla sem função". Um candidato natural é acionar o modo "o que faz esta tecla?" (hoje `Ctrl` + `Shift`, só no HDMI), mas isso muda o catálogo de comandos e fica para decisão da equipe e revisão do PRD.
- **Nome falado de `.`**: a tecla física mostra `,`, e o catálogo anuncia `"ponto"`. Avaliar se o anúncio deve passar a `"vírgula"` para coincidir com o keycap em pt-BR. É mudança de UX de voz, fora do escopo.
- **Constantes de tempo**: 1 ms e 20 ms foram suficientes nos testes de bancada, e o PRD §12 manda calibrar com o hardware final. Ficam configuráveis e devem ser revistas com o chicote definitivo.
