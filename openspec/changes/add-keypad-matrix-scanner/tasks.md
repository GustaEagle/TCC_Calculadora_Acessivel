## 1. Contrato de hardware: pinagem e mapa de switches

- [ ] 1.1 Em `software/hw_platform/keypad_pinout.py`, trocar os rótulos para 0-based (`C0..C6`, `L0..L5`, design D1) e as linhas para `L0=GPIO10/19`, `L1=GPIO9/21`, `L2=GPIO11/23`, `L3=GPIO17/11`, `L4=GPIO27/13` e `L5=GPIO22/15`, com as cores do mapa validado (C0 laranja, C1 roxo, C2 azul, C3 preto com final azul, C4 vermelho, C5 marrom, C6 laranja; L0 verde, L1 branco, L2 roxo, L3 roxo, L4 amarelo, L5 verde). Atualizar o docstring e os comentários que falam em numeração 1-based. Verificar: `python -c "import software.hw_platform.keypad_pinout"` importa sem erro.
- [ ] 1.2 Acrescentar `MatrixSwitch`, `SWITCHES` (`SW0..SW37` com coordenada e keycap, D2), `EMPTY_COORDS` e `switch_at(col, row)`. Registrar no docstring que `SWn` = `SW(n+1)` no KiCad. Verificar: `switch_at(3, 1)` devolve `SW9`/`7` e `switch_at(2, 1)` devolve `None`.
- [ ] 1.3 Estender `_validate()`: 38 switches, `SW#` sequencial, coordenadas únicas e dentro de 7x6, nenhuma sobre `EMPTY_COORDS`, e as 4 vazias + 38 = 42. Verificar: teste que monta um mapa inválido (coordenada repetida) e espera `ValueError`.
- [ ] 1.4 Atualizar `software/tests/test_keypad_pinout.py`: `ROW_BCM_PINS == (10, 9, 11, 17, 27, 22)`, rótulos iguais às nets, conflitos de periférico com os novos nomes (`L0`/`L1`/`L2` SPI0, `L3` SPI1 CE1, `C5`/`C6` UART0) e testes do mapa de switches (keycaps dos 38, posições vazias e GPIO27 no pino 13). Verificar: `python -m unittest software.tests.test_keypad_pinout -v`.
- [ ] 1.5 Atualizar `docs/raspberry-pi-4b/pinout.md` §6: tabelas 6.1/6.2 com os rótulos, os GPIOs e as cores novos, a tabela 6.3 com os nomes novos, a polaridade confirmada, o mapa `SW#`/`C#L#`/keycap e o §6.5 fechado (sentido e mapa confirmados; debounce 20 ms e estabilização 1 ms como valores de bancada). Verificar: `PinoutDocumentationTest` passa.

## 2. Scanner (`software/hw_platform/keypad_matrix.py`)

- [ ] 2.1 Criar `KeyEvent` (frozen, com `keycap`, `coord`, `switch`, `pressed`, `col_bcm`, `row_bcm`, `timestamp` e a propriedade `state`) e o protocolo `MatrixIO` (D3). O módulo não importa `gpiod` no topo. Verificar: `python -c "import software.hw_platform.keypad_matrix"` sem `gpiod` instalado.
- [ ] 2.2 Implementar `scan_once(io, settle_s, sleep)` com `try/finally` por coluna (D3/D5). Verificar: teste com `FakeMatrixIO` que registra a sequência de chamadas. Em nenhum instante há duas colunas ativas, `read_rows` só é chamado com uma coluna ativa, e uma exceção em `read_rows` ainda resulta em `float_column` antes de se propagar.
- [ ] 2.3 Implementar `Debouncer(debounce_s)` com relógio injetado e eventos de pressionamento e soltura. Posição vazia gera `logger.warning` uma vez e nenhum evento. Verificar: testes de pressionamento estável (1 evento), ressalto dentro de 20 ms (1 evento), soltura (1 evento "solto"), duas teclas simultâneas (2 eventos), pulso menor que 20 ms (0 eventos) e posição vazia (0 eventos, 1 aviso).
- [ ] 2.4 Implementar `GpiodMatrixIO`: conferir o rótulo do chip (`pinctrl-bcm2711`) e `line_info.used` antes de requisitar, fazer um único `request_lines` com o consumidor `calculadora-teclado`, usar as três `LineSettings` do design, montar a configuração completa das 13 linhas a cada `reconfigure_lines` (D5), ler com `get_values`, recusar uma segunda coluna ativa, e em `close()` aplicar `float_all()` (13 linhas em `FLOATING`) e depois `release()` em `try/finally`. Verificar: teste com um módulo `gpiod` falso injetado em `sys.modules` confirmando linhas com `PULL_DOWN`, exatamente 13 linhas em cada chamada, no máximo uma saída por chamada, release após flutuar tudo mesmo com exceção, e abertura recusada com chip errado ou linha ocupada (nenhum `request_lines` feito).
- [ ] 2.5 Implementar `MatrixKeyboard` (thread daemon, `open()` que devolve `None` sem hardware, `attach`/`detach`, `close()` idempotente com `join` + `float_all` + `close`; uma exceção de IO na thread faz `float_all` e encerra a thread). Verificar: teste com `FakeMatrixIO` e relógio falso mostrando que os eventos chegam ao sink, que `detach` descarta os eventos seguintes, que `close()` deixa tudo flutuando e que um erro de IO não deixa a thread em laço.

## 3. Catálogo de teclas

- [ ] 3.1 Em `software/ui/shared/keypad.py`, criar `entry_for_keycap()` com os aliases `x^-1`→`x⁻¹`, `Del`→`DEL` e `,`→`.` (D6), a constante `NO_FUNCTION_SPEECH` e o comentário corrigido sobre a `?`. Verificar: teste que percorre `SWITCHES` e exige entrada para os 37 keycaps diferentes de `?`, `None` para `?`, e `sen` → `("sen(", "asin(", None)`, `log` → `("log(", "ln(", "logbase(")` e `,` → `(".", None, ",")`.
- [ ] 3.2 Confirmar que o teclado na tela não muda: a posição da `?` continua sendo um espaço vazio. Verificar: `software/tests/test_video_blackout_keys.py` e `test_hdmi_layout_wiring.py` passam sem alteração.

## 4. Ponte para os fronts e entrada no app

- [ ] 4.1 Criar `software/ui/shared/matrix_input.py` com `MatrixInputPump` (D7). Verificar: `software/tests/test_matrix_input.py` com `FakeRoot` (padrão de `test_video_watch.py`) e teclado falso. Um evento "pressionado" de `7` chama `on_press("7", None, None)`, `sen` chama `on_press("sen(", "asin(", None)`, a soltura não chama nada, `?` chama `on_unmapped`, `tick` sempre reagenda e `stop()` faz `detach`.
- [ ] 4.2 Em `software/ui/lcd/app.py` e `software/ui/hdmi/app.py`, aceitar `keypad_matrix` no construtor, criar e iniciar o pump ligado a `_handle_token`, anunciar `NO_FUNCTION_SPEECH` em `on_unmapped` e parar o pump quando a janela é destruída. Manter os dois fronts espelhados. Verificar: teste sob Xvfb (padrão dos testes de GUI existentes) injetando `Ctrl` e `sen` pela ponte e confirmando `asin(` na expressão nos dois fronts.
- [ ] 4.3 Em `software/app.py`, adicionar `--keypad-matrix {auto,off}`, abrir o `MatrixKeyboard` uma vez em `run_mode()` e fechá-lo no `finally`, passá-lo por `start_front()` só aos fronts visuais, e instalar handlers de `SIGTERM`/`SIGHUP` que levantam `SystemExit` (D8). Verificar: testes em `test_entrypoint_dispatch.py` com `MatrixKeyboard.open` mockado. `off` não chama `open`, o scanner é o mesmo objeto nos dois fronts de uma troca, `close()` é chamado ao sair e após exceção, e o modo áudio não recebe o scanner.
- [ ] 4.4 Confirmar a degradação sem hardware: sem `gpiod` ou sem `/dev/gpiochip0`, `open()` devolve `None` com `logger.info` e o app arranca. Verificar: `python -m software.app --force-mode lcd` no PC (sob Xvfb no CI) sobe normalmente, e a suíte inteira passa sem `gpiod`.

## 5. Ferramenta de bring-up

- [ ] 5.1 Reescrever `software/tools/keypad_bringup.py` sobre `GpiodMatrixIO`/`scan_once`/`Debouncer` (D9): o modo padrão imprime os eventos com todos os campos, `--list`, `--toggle`, `--settle-ms`, `--debounce-ms`, a grade de switches vistos no `Ctrl+C` e `finally` com `close()`. Remover os backends `lgpio` e `RPi.GPIO`, a varredura bidirecional e o relatório de sentido. Verificar: `python3 software/tools/keypad_bringup.py --list` no PC imprime os 13 condutores e os 38 switches sem tocar em hardware.
- [ ] 5.2 Garantir que `--toggle` deixa todas as outras 12 linhas em `FLOATING` e restaura tudo ao sair. Verificar: teste com `gpiod` falso confirmando uma única saída por configuração.

## 6. Documentação e verificação final

- [ ] 6.1 Atualizar `docs/comandos-teclado.md`: a tecla `?` existe e anuncia "Tecla sem função", o teclado físico está ligado ao software, e as funções secundárias (`Ctrl`/`Shift`) funcionam pela matriz. Remover a nota "leitura da matriz por GPIO está pendente".
- [ ] 6.2 Procurar referências remanescentes aos rótulos 1-based e à polaridade antiga (`grep -rn '"L6"\|"C7"\|L1\.\.L6\|C1\.\.C7\|pull-up' software docs`) e corrigi-las. Verificar: nenhuma ocorrência relativa à matriz fica.
- [ ] 6.3 Rodar a suíte completa: `python -m unittest discover -s software/tests -v`. Verificar: tudo passa, sem `gpiod` e sem hardware.
- [ ] 6.4 Checklist de bancada no Pi (manual, fora do CI), acrescentado a `pinout.md` §6.5:
  - `python3 software/tools/keypad_bringup.py` com os 38 switches vistos e nenhum evento em posição vazia;
  - `pinctrl get 9-11,13-15,17,19-22,26-27` depois de `Ctrl+C` mostra as 13 em entrada sem pull;
  - o mesmo depois de `kill -TERM` no app;
  - `Ctrl` + `sen` produz arco seno nos dois fronts.
