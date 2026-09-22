# Especificação do pinout — Raspberry Pi 4 Model B (header J8)

**Conector:** J8, **40 pinos** (2×20), passo **2,54 mm**.  
**Âmbito:** apenas pinagem e funções de **uso corrente** no header; não substitui o [datasheet oficial](../RP-008341-DS-1-raspberry-pi-4-datasheet.pdf) para limites absolutos de corrente, derivações do SoC nem diagramas de bloco.

**Referências externas:** [pinout.xyz](https://pinout.xyz/) · [Documentação Raspberry Pi](https://www.raspberrypi.com/documentation/)

---

## 1. Convenções

| Termo | Significado |
| ----- | ----------- |
| **Pin** | Número **físico** no conector, **1…40** (estampado na silkbscreen da PCB como “1” junto ao canto da placa). |
| **BCM** | Numeração **Broadcom** do GPIO (uso típico em `gpiozero`, `RPi.GPIO`, `libgpiod`, overlays). |
| **Nome** | Rótulo habitual no **modo GPIO**; entre parêntesis, **função alternativa** mais citada para periféricos. |

**Orientação física:** com a placa vista de cima e os **conectores USB/Ethernet para baixo**, a coluna ímpar (**1, 3, …, 39**) fica em geral **perto da borda** da board; o **pino 1** é o canto que leva **3,3 V** (quadrado na PCB em muitos desenhos). Confirme sempre o **“1”** na sua unidade.

---

## 2. Requisitos elétricos (resumo)

- Todos os pinos marcados como **GPIO** operam a **3,3 V** lógicos. **Não** aplicar **5 V** a entradas GPIO — **não** são tolerantes a 5 V.
- Pinos **3V3** (1, 17): alimentação **3,3 V** limitada (capacidade total partilhada; ver datasheet).
- Pinos **5V** (2, 4): **5 V** (ligados ao rail de alimentação; origem depende do modo de alimentação da placa).
- **GND** (6, 9, 14, 20, 25, 30, 34, 39): referência comum.
- Corrente máxima **por GPIO** e **soma** de I/O: ver **datasheet** e notas de hardware; não assumir carga forte sem transistor/driver.

---

## 3. Tabela de pinos J8 (especificação)

| Pin | Sinal / função principal | BCM | Tipo |
| --- | ------------------------ | --- | ---- |
| 1 | 3V3 | — | Alimentação |
| 2 | 5V | — | Alimentação |
| 3 | GPIO2 — **I2C1 SDA** | 2 | GPIO / I2C |
| 4 | 5V | — | Alimentação |
| 5 | GPIO3 — **I2C1 SCL** | 3 | GPIO / I2C |
| 6 | GND | — | Terra |
| 7 | GPIO4 | 4 | GPIO |
| 8 | GPIO14 — **UART0 TXD** | 14 | GPIO / UART |
| 9 | GND | — | Terra |
| 10 | GPIO15 — **UART0 RXD** | 15 | GPIO / UART |
| 11 | GPIO17 — **SPI1 CE1** (ALT) | 17 | GPIO / SPI |
| 12 | GPIO18 — **SPI1 SCLK** (ALT) / **PWM0** / PCM_CLK | 18 | GPIO / SPI / PWM / PCM |
| 13 | GPIO27 | 27 | GPIO |
| 14 | GND | — | Terra |
| 15 | GPIO22 | 22 | GPIO |
| 16 | GPIO23 | 23 | GPIO |
| 17 | 3V3 | — | Alimentação |
| 18 | GPIO24 | 24 | GPIO |
| 19 | GPIO10 — **SPI0 MOSI** | 10 | GPIO / SPI |
| 20 | GND | — | Terra |
| 21 | GPIO9 — **SPI0 MISO** | 9 | GPIO / SPI |
| 22 | GPIO25 | 25 | GPIO |
| 23 | GPIO11 — **SPI0 SCLK** | 11 | GPIO / SPI |
| 24 | GPIO8 — **SPI0 CE0** | 8 | GPIO / SPI |
| 25 | GND | — | Terra |
| 26 | GPIO7 — **SPI0 CE1** | 7 | GPIO / SPI |
| 27 | GPIO0 — **ID_SD** (EEPROM HAT, I2C) | 0 | Reservado HAT / GPIO |
| 28 | GPIO1 — **ID_SC** (EEPROM HAT, I2C) | 1 | Reservado HAT / GPIO |
| 29 | GPIO5 | 5 | GPIO |
| 30 | GND | — | Terra |
| 31 | GPIO6 | 6 | GPIO |
| 32 | GPIO12 — **PWM0** | 12 | GPIO / PWM |
| 33 | GPIO13 — **PWM1** | 13 | GPIO / PWM |
| 34 | GND | — | Terra |
| 35 | GPIO19 — **SPI1 MISO** (ALT) / PCM_FS | 19 | GPIO / SPI / PCM |
| 36 | GPIO16 — **SPI1 CE0** (ALT) | 16 | GPIO / SPI |
| 37 | GPIO26 | 26 | GPIO |
| 38 | GPIO20 — **SPI1 MOSI** (ALT) / PCM_DIN | 20 | GPIO / SPI / PCM |
| 39 | GND | — | Terra |
| 40 | GPIO21 — PCM_DOUT (ALT) | 21 | GPIO / PCM |

**Nota:** **SPI1** só está disponível após ativar o controlador com **Device Tree overlay** (ex.: `spi1-1cs`, `spi1-2cs`, `spi1-3cs` em `config.txt`). Os pinos **MOSI / MISO / SCLK** acima são o mapeamento habitual no header; linhas **CE** (**chip enable** = **chip select**, **CS**) podem ser **reatribuídas** por parâmetros do overlay — ver README em `/boot/firmware/overlays/README` na imagem do SO.

---

## 3.1 SPI0 — sinais no J8 (bus principal)

Controlador **SPI0** (nós típicos `/dev/spidev0.0`, `/dev/spidev0.1`). **CE** = *chip enable* (sinônimo usual de **CS**, *chip select* / **SS**, *slave select*).

| Sinal | Função | BCM | Pin físico |
| ----- | ------ | --- | ---------- |
| **MOSI** | Master Out, Slave In | 10 | 19 |
| **MISO** | Master In, Slave Out | 9 | 21 |
| **SCLK** | *Serial clock* (relógio SPI) | 11 | 23 |
| **CE0** | Chip select 0 | 8 | 24 |
| **CE1** | Chip select 1 | 7 | 26 |

O SPI0 expõe **duas** linhas de chip select (**CE0**, **CE1**). Não há **CE2** no SPI0 neste header.

---

## 3.2 SPI1 — sinais habituais no J8 (bus auxiliar)

Controlador **SPI1** (ex.: `/dev/spidev1.x` quando ativo). Mapeamento **frequente** no conector (compatível com referências como [pinout.xyz — SPI](https://pinout.xyz/pinout/spi)); **confirmar** na sua imagem se usou overlay com `cs*_pin` personalizado.

| Sinal | BCM | Pin físico |
| ----- | --- | ---------- |
| **MOSI** | 20 | 38 |
| **MISO** | 19 | 35 |
| **SCLK** | 18 | 12 |
| **CE0** | 16 | 36 |
| **CE1** | 17 | 11 |

**CE2 (terceiro chip select):** o overlay **`spi1-3cs`** permite três linhas **CS**; os **números de GPIO** para **CS0 / CS1 / CS2** são **configuráveis** (parâmetros `cs0_pin`, `cs1_pin`, `cs2_pin` no README oficial dos overlays). O valor **padrão** do firmware pode **colidir** com o uso “didático” CE0 = pin 36 se não ler o overlay — **sempre** validar com a documentação da sua versão (`dtoverlay -h spi1-3cs` ou arquivo `README` dos overlays). O **GPIO21** (pin **40**) **não** faz parte deste mapa SPI1 habitual; mantém-se principalmente como **PCM** / GPIO.

---

## 4. Interfaces no header (mapa rápido)

| Interface | Pinos físicos | BCM |
| --------- | ------------- | --- |
| **I2C1** (uso geral, ex.: sensores, muitos HAT) | 3 (SDA), 5 (SCL) | 2, 3 |
| **UART0** | 8 (TX), 10 (RX) | 14, 15 |
| **SPI0** | 19 (**MOSI**), 21 (**MISO**), 23 (**SCLK**), 24 (**CE0**), 26 (**CE1**) | 10, 9, 11, 8, 7 |
| **SPI1** (com overlay) | 38 (**MOSI**), 35 (**MISO**), 12 (**SCLK**), 36 (**CE0**), 11 (**CE1**); **CE2** só com `spi1-3cs` e pinos conforme overlay | 20, 19, 18, 16, 17 |
| **EEPROM HAT** (I2C dedicado) | 27 (ID_SD), 28 (ID_SC) | 0, 1 |

No **Raspberry Pi 4** existem **UARTs adicionais** noutros pinos via configuração; não estão todas listadas nesta especificação resumida.

---

## 5. EEPROM de HAT (pinos 27 e 28)

Os pinos **27** e **28** estão ligados ao bus de **identificação de HAT** (EEPROM). Com **UPS HAT**, **Sense HAT** ou outras placas empilhadas que usem esse bus, **não** atribua estes pinos a **matriz de teclado** ou GPIO geral **sem** analisar **conflito elétrico e lógico** com a pilha de placas.

---

## 6. Matriz do teclado 6×7 — atribuição de GPIO

Teclado **Cherry MX hotswap** ligado **direto ao GPIO** por cabo flat, **sem** microcontrolador (PRD §6). O esquemático KiCad (`hardware/pcb/`) nomeia apenas as nets **`Row0…Row5`** e **`Col0…Col6`**; a correspondência com os pinos do J8 é a tabela abaixo.

**Fonte única de verdade em código:** [`software/hw_platform/keypad_pinout.py`](../../software/hw_platform/keypad_pinout.py) — o módulo valida na importação que cada GPIO existe no J8, que BCM e pino físico batem com a tabela do §3 e que nenhuma linha está repetida. [`software/tests/test_keypad_pinout.py`](../../software/tests/test_keypad_pinout.py) trava estes valores no CI.

> **Numeração:** tudo é **0-based** e o rótulo do chicote **é** a net do esquemático: **L0 = Row0**, **C0 = Col0**. Uma posição da grade escreve-se **`C#L#`** (coluna, linha), e os switches são **`SW0…SW37`** — os mesmos componentes são `SW1…SW38` na PCB do KiCad (**SWn aqui = SW(n+1) lá**).

**Polaridade confirmada no hardware** (o anodo de cada díodo 1N4148 fica do lado do switch/coluna, o catodo na net `RowN`):

| Condutor | Configuração |
| -------- | ------------ |
| Linhas `L0…L5` | entrada com **pull-down** |
| Coluna ativa (uma de cada vez) | saída em **HIGH**, sem bias |
| Colunas inativas | entrada **sem bias** (alta impedância) |

Uma linha lida em **HIGH** com a coluna `Cn` ativa significa switch fechado em `CnLm`. **Nunca** duas colunas em saída ao mesmo tempo, **nunca** uma linha em saída. O scanner está em [`software/hw_platform/keypad_matrix.py`](../../software/hw_platform/keypad_matrix.py) (libgpiod v2, `gpiochip0`, offset = BCM).

### 6.1 Colunas

| Rótulo | Net (KiCad) | Cor do fio | BCM | Pin | Função alternativa do pino |
| ------ | ----------- | ---------- | --- | --- | -------------------------- |
| **C0** | Col0 | Laranja | 26 | 37 | — |
| **C1** | Col1 | Roxo | 19 | 35 | SPI1 MISO (ALT) |
| **C2** | Col2 | Azul | 13 | 33 | PWM1 |
| **C3** | Col3 | Preto com final azul | 21 | 40 | PCM_DOUT (ALT) |
| **C4** | Col4 | Vermelho | 20 | 38 | SPI1 MOSI (ALT) |
| **C5** | Col5 | Marrom | 15 | 10 | **UART0 RXD** |
| **C6** | Col6 | Laranja | 14 | 8 | **UART0 TXD** |

### 6.2 Linhas

| Rótulo | Net (KiCad) | Cor do fio | BCM | Pin | Função alternativa do pino |
| ------ | ----------- | ---------- | --- | --- | -------------------------- |
| **L0** | Row0 | Verde | 10 | 19 | **SPI0 MOSI** |
| **L1** | Row1 | Branco | 9 | 21 | **SPI0 MISO** |
| **L2** | Row2 | Roxo | 11 | 23 | **SPI0 SCLK** |
| **L3** | Row3 | Roxo | 17 | 11 | SPI1 CE1 (ALT, só com overlay) |
| **L4** | Row4 | Amarelo | 27 | 13 | — |
| **L5** | Row5 | Verde | 22 | 15 | — |

13 condutores no total (6 linhas + 7 colunas), sem repetição de GPIO nem de pino físico. **Atenção:** GPIO27 é o **pino físico 13**; o pino físico 27 (EEPROM de HAT, §5) **não** é usado pela matriz.

> Uma versão anterior desta tabela tinha **Row0↔Row2** e **Row3↔Row5** trocadas — os mesmos seis GPIOs em outra ordem. A ordem acima foi conferida eletricamente, tecla a tecla.

### 6.3 Conflitos de função — o que tem de ficar desligado no boot

Seis das treze linhas ocupam pinos com periférico associado. Elas só se comportam como **GPIO comum** enquanto o firmware **não** ativar esse periférico — ver [`system/rpi-os/alpine/overlay/boot/usercfg.txt`](../../system/rpi-os/alpine/overlay/boot/usercfg.txt):

| Periférico | Pinos da matriz | Condição para a matriz funcionar |
| ---------- | --------------- | -------------------------------- |
| **UART0** | C6 (GPIO14), C5 (GPIO15) | `enable_uart=0` e **sem** `console=serial0` no `cmdline.txt` (a imagem usa `console=tty1`). **Custo:** sem consola série para depurar o boot; resta o HDMI/tty1. |
| **SPI0** | L2 (GPIO11), L1 (GPIO9), L0 (GPIO10) | **não** ligar `dtparam=spi=on`. O LCD Waveshare é HDMI, não SPI — nada no produto quer o SPI0. |
| **SPI1** (ALT) | L3 (GPIO17 = CE1) | **não** carregar overlay `spi1-*cs`. Sem overlay, SPI1 nem existe — conflito apenas teórico. |

**I2C1 (GPIO2/GPIO3, pinos 3 e 5) fica FORA da matriz de propósito.** É o barramento onde o UPS HAT lê tensão/corrente/capacidade no endereço **0x42** ([UPS_HAT.md](../waveshare/UPS_HAT.md), RF-06/RF-14): mantendo-o livre, a leitura de bateria usa o I2C **de hardware** (`dtparam=i2c_arm=on`, `/dev/i2c-1`), sem overlay `i2c-gpio` nem código fora do padrão da Waveshare.

> **Porque L3…L5 saíram de GPIO4/3/2 (pinos 7/5/3).** Além do UPS, **GPIO2 e GPIO3 são os únicos pinos do header com pull-ups de 1,8 kΩ para 3,3 V soldados na placa do Pi** — existem sempre, mesmo com o I2C desligado, e nenhuma configuração os remove. Numa linha de matriz lida com pull-down, esses pull-ups a manteriam sempre em HIGH (tecla sempre premida); como I2C, são exatamente os pull-ups que o barramento quer. Os pinos **11/13/15** (GPIO17/27/22) não têm periférico ativo nenhum e continuam a ser três **ímpares contíguos**, ou seja, o flat mantém a geometria.

> **O UPS HAT não é empilhável neste projeto.** O header dele é de 40 pinos **sem passagem** e o header do Pi está ocupado pelo flat do teclado, portanto a HAT liga-se **por fios** (5 V, GND, SDA no pino 3, SCL no pino 5) — ou alimenta o Pi pela saída USB 5 V dela. Confirmar no esquemático do lote antes de soldar.

Os pinos **27/28** (GPIO0/GPIO1, EEPROM de HAT — §5) **não** são usados pela matriz e não entram na lista de livres.

### 6.4 GPIO livres depois desta atribuição

**BCM:** 4, 5, 6, 7, 8, 12, 16, 18, 23, 24, 25 · **Pinos:** 7, 29, 31, 26, 24, 32, 36, 12, 16, 18, 22.

GPIO2/GPIO3 (pinos 3/5) **não** entram aqui: estão reservados ao I2C1 do UPS HAT (§6.3).

### 6.5 Mapa de switches e bring-up

Grade vista de frente, colunas `C0…C6` da esquerda para a direita. Cada célula: switch e keycap. As quatro posições **—** não têm switch (`C2L1`, `C2L2`, `C2L3`, `C4L4`); sinal nelas é defeito e o scanner só o regista no log.

| | C0 | C1 | C2 | C3 | C4 | C5 | C6 |
| - | -- | -- | -- | -- | -- | -- | -- |
| **L0** | SW0 `Pol` | SW1 `x!` | SW2 `Pi` | SW3 `(` | SW4 `)` | SW5 `%` | SW6 `e` |
| **L1** | SW7 `sen` | SW8 `cos` | — | SW9 `7` | SW10 `8` | SW11 `9` | SW12 `/` |
| **L2** | SW13 `tan` | SW14 `log` | — | SW15 `4` | SW16 `5` | SW17 `6` | SW18 `*` |
| **L3** | SW19 `x^-1` | SW20 `^` | — | SW21 `1` | SW22 `2` | SW23 `3` | SW24 `-` |
| **L4** | SW25 `?` | SW26 `nCr` | SW27 `√` | SW28 `0` | — | SW29 `,` | SW30 `+` |
| **L5** | SW31 `Ctrl` | SW32 `exp` | SW33 `Shift` | SW34 `Ans` | SW35 `=` | SW36 `AC` | SW37 `Del` |

A tecla **`?`** existe na placa mas **não tem função** no software: ela é lida e anuncia «Tecla sem função».

**Tempos (valores de bancada, PRD §12):** estabilização de **~1 ms** depois de ativar cada coluna, **debounce de ~20 ms**. Ambos são configuráveis no scanner e na ferramenta de bring-up; rever com o chicote definitivo.

**Checklist de bancada** (manual, no Pi; não corre no CI):

- `python3 software/tools/keypad_bringup.py` — premir as 38 teclas: cada uma aparece com `SW#`, `C#L#`, keycap e GPIOs, a grade final mostra 38 de 38, e nenhuma posição vazia aparece.
- Depois do `Ctrl+C`: `pinctrl get 9-11,13-15,17,19-22,26-27` mostra as 13 GPIOs em entrada sem pull (`ip pn`).
- O mesmo `pinctrl get` depois de `kill -TERM` no app (`python3 -m software.app`).
- Com o app aberto, `Ctrl` e depois `sen` na matriz insere o arco seno — nos dois fronts (LCD e monitor).

---

## 7. Diagrama visual

A imagem `Pinout.png` serve como **referência gráfica**. Pode corresponder a outro modelo no silkscreen (ex.: Pi 3 B+); a **numeração 1…40** e as **funções da tabela acima** aplicam-se ao **Pi 4 Model B** neste projeto.

![Pinout GPIO — header de 40 pinos (referência visual)](Pinout.png)

---

## 8. Artefactos relacionados no repositório

- [README.md](README.md) — índice da pasta (datasheet, CAD, links).
- Modelo 3D: [`../cad/raspberry-pi-4-model-b/`](../cad/raspberry-pi-4-model-b/)
