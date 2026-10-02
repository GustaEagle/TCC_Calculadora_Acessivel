# Teclado físico da calculadora (matriz 6×7)

Referência completa do **teclado do produto**: o que cada tecla faz sozinha, com `Ctrl` e com `Shift`, onde ela fica na grade e como a matriz é lida pelo Raspberry Pi.

Este é o teclado **oficial** da calculadora (RF-05: a entrada é exclusivamente pelo teclado físico). O teclado comum de PC é uma conveniência de desenvolvimento e cobre só parte destes comandos — está documentado em [comandos-teclado.md](comandos-teclado.md).

**Fonte da verdade no código:**

| Ficheiro | O que define |
| -------- | ------------ |
| [`hw_platform/keypad_pinout.py`](../../software/hw_platform/keypad_pinout.py) | Posição de cada tecla (`SW#`, `C#L#`, keycap) e o GPIO de cada linha/coluna |
| [`ui/shared/keypad.py`](../../software/ui/shared/keypad.py) | Catálogo de funções (principal, `Ctrl`, `Shift`) e os nomes falados |
| [`hw_platform/keypad_matrix.py`](../../software/hw_platform/keypad_matrix.py) | Varredura por GPIO, debounce e eventos de tecla |
| [`ui/shared/matrix_input.py`](../../software/ui/shared/matrix_input.py) | Entrega dos eventos ao front (Tk) |

As tabelas abaixo foram **geradas a partir desses módulos** — se o código mudar, elas ficam desatualizadas; regere-as em vez de as editar à mão.

---

## 1. Layout físico

38 teclas numa grade de **6 linhas × 7 colunas**. As 4 posições marcadas `·` não têm switch montado — sinal nelas é defeito de hardware, nunca tecla.

```
        C0      C1      C2      C3      C4      C5      C6
  L0   Pol      x!      Pi       (       )       %       e
  L1   sen     cos       ·       7       8       9       /
  L2   tan     log       ·       4       5       6       *
  L3  x⁻¹       ^        ·       1       2       3       -
  L4     ?     nCr       √       0       ·       ,       +
  L5  Ctrl     exp   Shift     Ans       =      AC     Del
```

- **Bloco esquerdo** (`C0`–`C2`): funções científicas e os dois modificadores.
- **Bloco direito** (`C3`–`C6`): dígitos, operadores e as teclas de controlo.
- `C#L#` é a **coordenada elétrica** (coluna, linha), a mesma que o scanner usa nos seus eventos e que aparece no log de bring-up.

Layout visual para impressão/edição: [keyboard-layout/](../keyboard-layout/README.md) (formato KLE). Ligação elétrica de cada fio: [pinout.md §6](../raspberry-pi-4b/pinout.md).

---

## 2. `Ctrl` e `Shift` são fixos, não de segurar

Os modificadores funcionam como **interruptor (toggle)** — nunca é preciso pressionar duas teclas ao mesmo tempo:

1. Pressione `Ctrl` (ou `Shift`). O indicador `CTRL` / `SHIFT` acende no topo da tela e a voz anuncia «Controle ativo» / «Shift ativo».
2. Pressione a tecla seguinte — sai a **função secundária** dela.
3. O modificador **desliga-se sozinho** assim que uma tecla que tem função para ele é usada.

> Decisão de acessibilidade: quem opera com uma mão só, ou sem enxergar a tela, não consegue segurar um modificador e alcançar outra tecla ao mesmo tempo.

Detalhes que importam na prática:

- Pressionar `Ctrl` de novo **cancela** («Controle desativado»).
- Se a tecla pressionada **não tiver** função para o modificador ativo, ela age normalmente e o modificador **continua ligado** até ser usado ou cancelado.
- `Ctrl` e `Shift` **juntos** (os dois indicadores acesos) entram no modo *“o que faz esta tecla?”*, só no front HDMI: a próxima tecla **não é executada**, a voz apenas descreve as três funções dela.

---

## 3. Catálogo completo das 38 teclas

Diferente do teclado de PC, na matriz **toda** tecla traz as suas funções secundárias.

| Tecla | Sozinha | Com `Ctrl` | Com `Shift` | Posição | Switch |
| ----- | ------- | ---------- | ----------- | ------- | ------ |
| `Pol` | `polar(` | `rect(` | — | `C0L0` | SW0 |
| `x!` | `!` | — | — | `C1L0` | SW1 |
| `Pi` | `π` | `e` | — | `C2L0` | SW2 |
| `(` | `(` | — | — | `C3L0` | SW3 |
| `)` | `)` | — | — | `C4L0` | SW4 |
| `%` | `%` | — | — | `C5L0` | SW5 |
| `e` | `e` | — | — | `C6L0` | SW6 |
| `sen` | `sen(` | `asin(` | — | `C0L1` | SW7 |
| `cos` | `cos(` | `acos(` | — | `C1L1` | SW8 |
| `7` | `7` | — | — | `C3L1` | SW9 |
| `8` | `8` | — | — | `C4L1` | SW10 |
| `9` | `9` | — | — | `C5L1` | SW11 |
| `/` | `/` | — | **RAD/DEG** | `C6L1` | SW12 |
| `tan` | `tan(` | `atan(` | — | `C0L2` | SW13 |
| `log` | `log(` | `ln(` | `logbase(` | `C1L2` | SW14 |
| `4` | `4` | — | — | `C3L2` | SW15 |
| `5` | `5` | — | — | `C4L2` | SW16 |
| `6` | `6` | — | — | `C5L2` | SW17 |
| `*` | `*` | — | — | `C6L2` | SW18 |
| `x⁻¹` | `inv(` | — | — | `C0L3` | SW19 |
| `^` | `^` | — | — | `C1L3` | SW20 |
| `1` | `1` | — | — | `C3L3` | SW21 |
| `2` | `2` | — | — | `C4L3` | SW22 |
| `3` | `3` | — | — | `C5L3` | SW23 |
| `-` | `-` | — | — | `C6L3` | SW24 |
| `?` | **sem função** | — | — | `C0L4` | SW25 |
| `nCr` | `nCr(` | `nPr(` | — | `C1L4` | SW26 |
| `√` | `sqrt(` | — | — | `C2L4` | SW27 |
| `0` | `0` | — | — | `C3L4` | SW28 |
| `,` | `.` (ponto decimal) | — | `,` (separador de argumentos) | `C5L4` | SW29 |
| `+` | `+` | — | — | `C6L4` | SW30 |
| `Ctrl` | liga/desliga `CTRL` | — | — | `C0L5` | SW31 |
| `exp` | `exp(` | — | — | `C1L5` | SW32 |
| `Shift` | liga/desliga `SHIFT` | — | — | `C2L5` | SW33 |
| `Ans` | resposta anterior | **Histórico** | — | `C3L5` | SW34 |
| `=` | calcula | **Última resposta** | **Última resposta** | `C4L5` | SW35 |
| `AC` | limpa tudo | **Apaga/religa as telas** | — | `C5L5` | SW36 |
| `Del` | apaga o último item | — | — | `C6L5` | SW37 |

**Sem função secundária:** `x!`, `x⁻¹`, `^`, `√`, `exp`, `%`, `e`, `(`, `)`, `Del`, os dígitos e `+ - *`.

### A tecla `,` e o ponto decimal

A tecla impressa `,` produz **`.`** (ponto decimal) quando pressionada sozinha, e **`,`** (vírgula) com `Shift`. O motor usa ponto para decimais e vírgula para separar argumentos: `nCr(5,2)` digita-se `nCr` `5` `Shift` `,` `2` `)`.

### A tecla `?`

A `?` (SW25, `C0L4`) **existe na placa** mas não tem função no catálogo do PRD §5. Ao ser pressionada, a voz diz «Tecla sem função» e nada entra na expressão — sem esse retorno, quem não vê a tela concluiria que a tecla está avariada. Na tela, a posição correspondente fica vazia.

---

## 4. Comandos que não inserem símbolo

| Comando | Teclas | O que faz |
| ------- | ------ | --------- |
| **Histórico** | `Ctrl` → `Ans` | Últimos cálculos **bem-sucedidos** (10 no HDMI, 6 no LCD), do mais recente ao mais antigo. No LCD abre um painel; qualquer outra tecla o fecha |
| **Última resposta** | `Ctrl` → `=` ou `Shift` → `=` | Reanuncia o último resultado **completo** (sem o truncamento do display), **sem recalcular** e **sem tocar** na expressão em curso |
| **Graus ↔ radianos** | `Shift` → `/` | Alterna RAD/DEG; a voz confirma o modo novo |
| **Apagar/religar telas** | `Ctrl` → `AC` | Desliga **todas** as saídas de vídeo (ver §5). Não limpa a expressão |
| **Limpar tudo** | `AC` | Limpa expressão e último resultado. Com as telas apagadas, **religa-as** antes de limpar |
| **Apagar um item** | `Del` | Remove o último caractere — funções (`sen(`, `log(`, `nCr(`, …) saem como **bloco único**, não letra a letra |

**Não existe tecla dedicada de histórico.** O atalho `Ctrl` + `Ans` foi escolhido por usar só teclas que já existem na matriz, de modo que o comando seja idêntico no hardware e no PC.

Sem resposta anterior na sessão, a última resposta devolve o aviso **WRN-010** («Não há resposta anterior»). Erros não entram no histórico.

### Encadeamento depois de um `=`

Logo após um `=` bem-sucedido, a mesma tecla faz coisas diferentes:

| Tecla seguinte | Comportamento |
| -------------- | ------------- |
| Operador (`+ - * / ^`) | Continua a partir do resultado: a expressão vira `Ans` + operador |
| Dígito, função, `π`, `e`, `Ans` | Começa expressão nova (limpa a anterior automaticamente) |
| Dois operadores seguidos | O segundo **substitui** o primeiro; a voz anuncia «Substituindo» |

---

## 5. Apagar e religar as telas (`Ctrl` + `AC`)

A calculadora não depende da tela (RF-04): para quem não a usa, um painel aceso só gasta bateria do UPS e expõe a conta a quem estiver por perto. `Ctrl` e depois `AC` **desliga todas as saídas de vídeo** — o LCD e também o monitor externo, se estiver ligado. Repetir o atalho religa.

- **Por que é função secundária do `AC`:** a matriz não tem tecla livre. Como qualquer função secundária, **não limpa a expressão** e **consome o `Ctrl`**.
- **A calculadora continua inteira com as telas apagadas:** as teclas chegam, os resultados são calculados e anunciados, e a expressão em curso, o `Ans`, o histórico e o modo graus/radianos ficam intactos. Não é o modo somente áudio.
- **Confirmação por voz, sempre** (aviso **WRN-013**, PRD §13): «Aviso 013. Telas desligadas. Para religar, pressione AC.» Ao religar, a voz diz em que painel a tela voltou. Se o comando falhar, a voz diz que **não** foi possível — nunca anuncia um desligamento que não aconteceu.
- **`AC` sozinho religa.** Quem apagar as telas por engano não fica diante de um aparelho aparentemente morto: `AC` religa e depois limpa a expressão, como de costume. Com as telas acesas, `AC` não mexe no vídeo.
- **Ao religar vale a prioridade de sempre** (PRD §7.2): monitor externo se estiver ligado, senão o LCD. Se um monitor for ligado durante o apagão, a UI passa para ele **ainda apagada**.
- **Não é guardado:** a calculadora arranca sempre com a tela acesa.

---

## 6. Como a matriz é lida

Nenhum microcontrolador no meio: os switches ligam **direto ao GPIO** do Pi 4 por cabo flat (PRD §6).

| Característica | Valor | Onde |
| -------------- | ----- | ---- |
| Polaridade | Coluna ativa em **HIGH**; linhas são entradas com **pull-down**; colunas ociosas flutuam | `keypad_matrix.py` |
| Estabilização | **1 ms** depois de ativar a coluna, antes de ler as linhas | `SETTLE_S` |
| Debounce | **20 ms** — um estado novo só conta se durar isso | `DEBOUNCE_S` |
| Varredura | ~**100 varreduras/s** (pausa de 2 ms entre passagens) | `SWEEP_PAUSE_S` |
| Controlador | `/dev/gpiochip0`, rótulo `pinctrl-bcm2711` (só Pi 4) | `GPIOCHIP_*` |

- **Teclas simultâneas são seguras:** cada switch tem um **1N4148** em série, o que elimina o *ghosting* (tecla fantasma) da leitura.
- **A tecla conta ao pressionar.** O evento de soltar é lido para o debounce mas **descartado** pelo front — soltar nunca executa nada.
- Os valores de debounce e estabilização são **de bancada**; o PRD §12 manda recalibrá-los com o hardware final.
- No Pi 4 o offset de cada linha no `gpiochip0` **é** o número BCM. Isso não vale noutros SBCs (no Pi 5 o header é o chip RP1), por isso o scanner confere o rótulo do chip antes de supor a equivalência.

---

## 7. Ligar, desligar e diagnosticar

A matriz é ligada **automaticamente** quando o app corre no Raspberry Pi 4 com `gpiod` (libgpiod v2) disponível; noutro computador o app arranca na mesma, só sem ela.

```bash
python -m software.app                      # auto: liga a matriz se houver Pi 4 + gpiod
python -m software.app --keypad-matrix off  # nunca toca em GPIO (PC, CI, depuração)
```

**Testar as teclas sem abrir o app** (mostra `SW#`, `C#L#` e keycap de cada pressão):

```bash
python3 software/tools/keypad_bringup.py
```

> Pare o app antes — ele segura as mesmas GPIOs, e a segunda instância não consegue reservá-las.

Se uma tecla não responder, a ordem de diagnóstico é: **bring-up** (a matriz vê a tecla?) → [pinout.md §6.3](../raspberry-pi-4b/pinout.md) (algum periférico reclamou o pino no boot?) → cor do fio contra a tabela de [pinout.md §6.1/§6.2](../raspberry-pi-4b/pinout.md).

---

## 8. Limitações conhecidas

- **No modo somente áudio a matriz não funciona.** Esse modo (quando nenhuma tela é reconhecida) lê linhas digitadas num teclado de PC. Para usar a calculadora sem olhar para a tela, apague as telas com `Ctrl` + `AC`: o front continua ativo e a matriz também.
- **Uma interface ligada no boot mata a linha em silêncio.** UART0, SPI0 e SPI1 partilham pinos com a matriz; enquanto ficarem desligadas no `usercfg.txt` o pino é GPIO comum. Se alguém as ligar, a linha correspondente para de responder sem erro visível — ver [pinout.md §6.3](../raspberry-pi-4b/pinout.md).
- **`GPIO2`/`GPIO3` (I2C1) estão deliberadamente fora da matriz:** é o barramento do UPS HAT (0x42, RF-06/RF-14) e são os únicos pinos do header com pull-ups de 1,8 kΩ soldados — bons para I2C, maus para linha de matriz.
- **O modo “o que faz esta tecla?”** (`Ctrl` + `Shift`) existe só no front HDMI; o LCD ainda não o tem.
- **Apagar as telas atua no servidor X** (`xrandr --off`): fora do Raspberry Pi, sem X, o comando é registado no log e a voz avisa que não foi possível — a calculadora segue normal.

---

## Ver também

- [comandos-teclado.md](comandos-teclado.md) — os mesmos comandos no **teclado de PC** (desenvolvimento e testes)
- [pinout.md §6](../raspberry-pi-4b/pinout.md) — GPIO de cada linha e coluna, cor de fio, conflitos de periférico
- [keyboard-layout/](../keyboard-layout/README.md) — layout físico no formato KLE
- [PRD.md](../produto/PRD.md) §5 (catálogo de funções), §6 (teclado), §13 (códigos de aviso)
