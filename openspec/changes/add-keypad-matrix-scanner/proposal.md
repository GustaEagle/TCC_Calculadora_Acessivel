## Why

O RF-05 exige que a calculadora aceite entrada **exclusivamente pelo teclado físico** do produto, e o RF-11 exige debounce nesse teclado. Hoje nenhum dos dois é cumprido: [`hw_platform/keyboard.py`](../../../software/hw_platform/keyboard.py) só mapeia o teclado de PC, e `docs/comandos-teclado.md` registra que "a leitura da matriz por GPIO está pendente". A matriz 6x7 foi agora **validada eletricamente no hardware** (Raspberry Pi 4, `gpiochip0`, libgpiod 2.x): sabe-se que polaridade funciona, que GPIO é cada linha e coluna, e que switch está em cada coordenada.

O que está no repositório diverge desse resultado:

- **A pinagem das linhas está errada.** [`keypad_pinout.py`](../../../software/hw_platform/keypad_pinout.py) põe `Row0` em GPIO11 e `Row5` em GPIO17. No hardware testado, `L0` é GPIO10 e `L5` é GPIO22: `Row0`↔`Row2` e `Row3`↔`Row5` estão trocadas. O conjunto de GPIOs é o mesmo, então os testes atuais passam, mas o scanner leria as teclas nas linhas erradas. Várias cores de fio também mudaram.
- **A polaridade da única ferramenta de GPIO é outra.** [`tools/keypad_bringup.py`](../../../software/tools/keypad_bringup.py) põe as 13 vias em pull-up e aciona em 0 V, varrendo nos dois sentidos porque a orientação dos diodos era desconhecida. A combinação confirmada é **coluna ativa em saída HIGH, linhas em entrada com pull-down, colunas inativas em entrada sem pull**. O esquemático confirma isso: na PCB (`hardware/pcb/TCC-09-05-2026`) o anodo de cada diodo `Dn` fica do lado do switch e da coluna, e o catodo na net `RowN`.
- **A tecla `?` existe.** O `keypad.py`, o `comandos-teclado.md` e a mudança `add-video-blackout-shortcut` afirmam que a tecla `?` dos exports KLE "não existe na matriz real". A PCB tem `SW26` em `Col0`/`Row4`, e o mapa validado lista `SW25 = C0L4 = ?`.

Sem esta mudança, o produto no Pi só funciona com um teclado de PC ligado por USB, o que contradiz o RF-05 e o conceito de acessibilidade do TCC.

## What Changes

- **Pinagem corrigida para o hardware validado.** Em `keypad_pinout.py`, as linhas passam a ser `L0=GPIO10`, `L1=GPIO9`, `L2=GPIO11`, `L3=GPIO17`, `L4=GPIO27` e `L5=GPIO22`. As colunas mantêm os GPIOs (`C0=26 … C6=14`), e as cores dos fios são atualizadas. **BREAKING (interno):** os rótulos de chicote passam de 1-based (`L1..L6`, `C1..C7`) para **0-based** (`L0..L5`, `C0..C6`), igual às nets do KiCad (`Row0..`, `Col0..`) e às coordenadas `C#L#` usadas na bancada. A dupla numeração deixa de existir.
- **Mapa de switches como contrato de hardware.** O mesmo módulo passa a declarar os 38 switches `SW0..SW37` com coordenada `C#L#` e keycap, e as 4 coordenadas sem switch (`C2L1`, `C2L2`, `C2L3`, `C4L4`). A validação na importação recusa coordenadas repetidas, fora da grade ou em posição vazia. A correspondência com o KiCad fica registrada: `SWn` aqui é `SW(n+1)` na PCB.
- **Novo scanner da matriz por libgpiod v2** (`software/hw_platform/keypad_matrix.py`):
  - As 13 GPIOs são requisitadas **uma única vez por processo**.
  - Cada coluna é ativada em HIGH **uma de cada vez**, e todas as linhas são lidas numa só chamada após cerca de 1 ms de estabilização.
  - A coluna volta a flutuar num `try/finally`.
  - O debounce é temporal, de cerca de 20 ms (RF-11).
  - Cada evento de pressionamento ou soltura informa keycap, `C#L#`, `SW#`, estado, GPIO da coluna e GPIO da linha.
  - Ao encerrar, inclusive por exceção, `Ctrl+C` ou `SIGTERM`, as 13 GPIOs voltam a entrada sem bias antes de serem liberadas.
  - A lógica de varredura e de debounce fica separada do acesso ao `gpiod` por uma interface injetável, e é testável sem hardware.
- **Integração na arquitetura existente, sem laço paralelo concorrente com o Tk.** A varredura roda numa thread própria, porque bloquear 7 ms por varredura no laço do Tk travaria a UI. Os eventos vão para uma fila. Cada front drena essa fila no próprio laço Tk (`root.after`), no mesmo padrão do `VideoOutputWatch`, e entrega o pressionamento ao `_handle_token()` que já existe. Ctrl, Shift, histórico, blackout e anúncios por voz passam pelo mesmo caminho do teclado de PC. O scanner pertence ao `run_mode()`, como o `CalculatorState`, e atravessa a troca de front do RF-09 sem liberar as GPIOs.
- **Funções secundárias pela matriz.** Na matriz, cada keycap é resolvido para a entrada completa do catálogo `keypad.py` (primária, `Ctrl` e `Shift`). Assim `Ctrl` + `sen` dá `asin(` e `Shift` + `log` dá `logbase(` também no teclado físico. Hoje isso só funciona nos botões da tela.
- **Ferramenta de bring-up reescrita sobre o scanner.** A varredura bidirecional com pull-up e os backends `lgpio` e `RPi.GPIO` saem, porque usam uma polaridade que contradiz a validada. Ficam `--list` (agora com o mapa de switches) e `--toggle` (localizar um fio com multímetro). O modo padrão imprime os eventos com todos os campos e, no `Ctrl+C`, a grade de switches já vistos.
- **Opção de linha de comando** `--keypad-matrix {auto,off}` no `software.app`. Em `auto` (padrão), a matriz é ligada quando o `gpiochip0` do Pi 4 está disponível e o app segue só com o teclado de PC quando não está (PC e CI). Em `off`, o app nunca toca em GPIO.
- **Documentação:** `docs/raspberry-pi-4b/pinout.md` §6 (tabelas, rótulos 0-based, polaridade confirmada, mapa de switches, §6.5 fechado) e `docs/comandos-teclado.md` (a `?` existe e não tem função, o teclado físico está ligado e as funções secundárias funcionam na matriz).

## Capabilities

### New Capabilities
- `keypad-matrix`: leitura da matriz física 6x7 por GPIO. Cobre a pinagem validada, a polaridade elétrica e as invariantes de segurança (nunca duas colunas em saída e nunca linha em saída), a varredura com estabilização, o debounce, os eventos de pressionamento e soltura com identificação completa, o mapa de switches e keycaps, a liberação segura das GPIOs e a entrega das teclas aos fronts visuais.

### Modified Capabilities
- `hdmi-ui`: o cenário "Entrada exclusivamente por teclado físico" do requisito "Paridade de acessibilidade entre fronts" cita `hw_platform/keyboard.py` como o mapeamento do teclado físico. Passa a exigir a matriz GPIO como fonte de entrada do produto, com o adaptador de PC como meio de desenvolvimento.

## Impact

- **Código alterado:**
  - `software/hw_platform/keypad_pinout.py`: pinagem das linhas, rótulos 0-based, cores, mapa de switches e validação.
  - `software/hw_platform/keypad_matrix.py`: **novo**.
  - `software/ui/shared/matrix_input.py`: **novo**, a ponte entre a fila e o Tk, compartilhada pelos dois fronts.
  - `software/ui/shared/keypad.py`: resolução keycap → entrada do catálogo e frase da tecla `?`.
  - `software/ui/lcd/app.py` e `software/ui/hdmi/app.py`: recebem o scanner e ligam a ponte.
  - `software/app.py`: posse do scanner em `run_mode()`, `--keypad-matrix` e `SIGTERM`/`SIGHUP` → encerramento limpo.
  - `software/tools/keypad_bringup.py`: reescrita sobre o scanner.
- **Sem alteração:** `software/core/`, que não sabe que existe GPIO. Também ficam como estão `software/hw_platform/keyboard.py`, que continua sendo o adaptador de PC, e o catálogo matemático do PRD §5.
- **Testes:** `software/tests/test_keypad_pinout.py` é atualizado para a pinagem nova. Entram `test_keypad_matrix.py` (varredura, invariantes, debounce e encerramento, com IO simulado e um `gpiod` falso) e `test_matrix_input.py` (ponte Tk com uma raiz falsa, no padrão de `test_video_watch.py`). A suíte continua rodando sem `gpiod` e sem hardware no CI (Python 3.11).
- **Dependências:** nenhuma nova. Usa `py3-libgpiod` (Alpine, 2.2.4, já em `system/rpi-os/alpine/packages`) ou `python3-libgpiod` (Raspberry Pi OS 13), ambos com a API v2. O import é tardio, então o PC não precisa do pacote.
- **Requisitos cobertos:** RF-05 (entrada pelo teclado físico, mapeamento documentado), RF-11 (debounce), RF-08 (a leitura não bloqueia o Tk nem o TTS), RF-09/RNF-03 (o scanner sobrevive à troca de front) e RNF-04 (hardware isolado em `hw_platform/`).
- **Risco principal:** uma coluna ficar em HIGH se o processo morrer no meio da varredura. A mitigação é o `try/finally` por coluna, a restauração completa no encerramento e o tratamento de `SIGTERM`/`SIGHUP`. Num `SIGKILL`, o kernel libera a requisição ao fechar o descritor. Registrado para conferência com `pinctrl get` no bring-up.

## Não-objetivos

- **Não** alterar o escopo matemático do PRD §5 nem acrescentar funções. A tecla `?` passa a ser **reconhecida**, mas **não recebe função** de cálculo (ver design, questões em aberto).
- **Não** acoplar `software/core/` a GPIO, a `gpiod` ou a threads.
- **Não** ligar a matriz ao modo somente áudio (`AudioOnlyCalculator`) nesta mudança. Ele continua lendo linhas do `stdin`. Levar a matriz até lá exige extrair a máquina de teclas (Ctrl, Shift, histórico) dos fronts Tk e fica para uma mudança própria. A limitação está registrada no design.
- **Não** alterar a PCB, o chicote nem os arquivos KLE.
- **Não** mudar a polaridade confirmada (coluna HIGH, linhas com pull-down) para saída LOW com pull-up.
- **Não** acrescentar linhas `gpio=` ao `usercfg.txt`. No reset, o BCM2711 já deixa GPIO9–27 como entrada com pull-down, e nenhum pino fica em saída antes do app.
- **Não** suportar Raspberry Pi 5 nem outros chips. O scanner confere o rótulo do `gpiochip0` e recusa o que não for o do Pi 4, em vez de supor que offset é igual a BCM.
