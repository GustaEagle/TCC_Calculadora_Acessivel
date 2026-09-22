Preciso que você localize e atualize o código Python chamado **`keypad pinout.py`** — o nome pode aparecer com espaços, hífens ou underscores. Inspecione primeiro o código existente, sua arquitetura, dependências e a versão do `libgpiod` utilizada. Depois, implemente o novo reconhecimento da matriz sem remover funcionalidades existentes que não conflitem com esta pinagem.

O equipamento é um **Raspberry Pi 4**, executando Raspberry Pi OS/Raspbian 13. A matriz foi testada com `gpiochip0` e `libgpiod` 2.x. Os offsets de linha do `gpiochip0` coincidem com os números BCM abaixo.

## Configuração elétrica confirmada

Os diodos e a matriz funcionaram corretamente desta maneira:

- As **linhas** ficam como entradas com **pull-down**.
- Uma única **coluna por vez** é configurada como saída em **HIGH**.
- As demais colunas permanecem como entradas em alta impedância, com bias desabilitado.
- Depois de ler todas as linhas, a coluna ativa volta imediatamente para entrada em alta impedância.
- Uma linha em HIGH durante a ativação de uma coluna significa que o switch daquela coordenada está pressionado.
- Nunca deixe duas colunas como saídas ao mesmo tempo.
- Nunca configure linha e coluna como saídas com níveis opostos.
- Ao encerrar o programa, inclusive em exceções ou `Ctrl+C`, devolva todas as GPIOs da matriz para entrada com bias desabilitado.
- Use debounce de aproximadamente **20 ms**.
- Um tempo de estabilização de aproximadamente **1 ms** após ativar cada coluna funcionou nos testes.

Não altere essa polaridade para saída LOW com pull-up sem evidência concreta no código ou hardware. A combinação confirmada foi:

```text
coluna ativa = saída HIGH
linhas = entradas com pull-down
colunas inativas = entradas sem pull
```

## Mapeamento das colunas

```text
C0 = GPIO26 = pino físico 37 = laranja
C1 = GPIO19 = pino físico 35 = roxo
C2 = GPIO13 = pino físico 33 = azul
C3 = GPIO21 = pino físico 40 = preto com final azul
C4 = GPIO20 = pino físico 38 = vermelho
C5 = GPIO15 = pino físico 10 = marrom
C6 = GPIO14 = pino físico 8  = laranja
```

## Mapeamento das linhas

```text
L0 = GPIO10 = pino físico 19 = verde
L1 = GPIO9  = pino físico 21 = branco
L2 = GPIO11 = pino físico 23 = roxo
L3 = GPIO17 = pino físico 11 = roxo
L4 = GPIO27 = pino físico 13 = amarelo
L5 = GPIO22 = pino físico 15 = verde
```

Atenção: **GPIO27 está no pino físico 13**. O **pino físico 27 não é utilizado** pela matriz.

## Keycaps e switches

Use switches numerados de `SW0` até `SW37`:

```text
SW0  = C0L0 = Pol
SW1  = C1L0 = x!
SW2  = C2L0 = Pi
SW3  = C3L0 = (
SW4  = C4L0 = )
SW5  = C5L0 = %
SW6  = C6L0 = e

SW7  = C0L1 = sen
SW8  = C1L1 = cos
SW9  = C3L1 = 7
SW10 = C4L1 = 8
SW11 = C5L1 = 9
SW12 = C6L1 = /

SW13 = C0L2 = tan
SW14 = C1L2 = log
SW15 = C3L2 = 4
SW16 = C4L2 = 5
SW17 = C5L2 = 6
SW18 = C6L2 = *

SW19 = C0L3 = x^-1
SW20 = C1L3 = ^
SW21 = C3L3 = 1
SW22 = C4L3 = 2
SW23 = C5L3 = 3
SW24 = C6L3 = -

SW25 = C0L4 = ?
SW26 = C1L4 = nCr
SW27 = C2L4 = √
SW28 = C3L4 = 0
SW29 = C5L4 = ,
SW30 = C6L4 = +

SW31 = C0L5 = Ctrl
SW32 = C1L5 = exp
SW33 = C2L5 = Shift
SW34 = C3L5 = Ans
SW35 = C4L5 = =
SW36 = C5L5 = AC
SW37 = C6L5 = Del
```

As seguintes coordenadas não possuem switch e não devem gerar keycap:

```text
C2L1
C2L2
C2L3
C4L4
```

## Estrutura sugerida para libgpiod 2.x

Avalie como incorporar isto à arquitetura já existente. Uma implementação compatível com o hardware testado utiliza conceitos equivalentes a:

```python
from gpiod.line import Bias, Direction, Value

FLOATING = gpiod.LineSettings(
    direction=Direction.INPUT,
    bias=Bias.DISABLED,
)

ROW_INPUT = gpiod.LineSettings(
    direction=Direction.INPUT,
    bias=Bias.PULL_DOWN,
)

COLUMN_HIGH = gpiod.LineSettings(
    direction=Direction.OUTPUT,
    bias=Bias.DISABLED,
    output_value=Value.ACTIVE,
)
```

As GPIOs devem preferencialmente ser requisitadas uma única vez pelo processo. Durante a varredura:

```python
for gpio_coluna in colunas:
    request.reconfigure_lines({gpio_coluna: COLUMN_HIGH})
    aguardar_aproximadamente_1_ms()
    ler_todas_as_linhas()
    request.reconfigure_lines({gpio_coluna: FLOATING})
```

Implemente o retorno da coluna para `FLOATING` usando `try/finally`, para que uma exceção durante a leitura não deixe a coluna ativa.

O programa deve reconhecer pressionamento e soltura, aplicar debounce e disponibilizar pelo menos:

```text
keycap
coordenada C#L#
switch SW#
estado pressionado/solto
GPIO da coluna
GPIO da linha
```

Se o código já possuir callbacks, eventos, filas, interface gráfica ou integração com outra aplicação, adapte a leitura à estrutura existente em vez de criar um loop paralelo incompatível.

## Histórico de diagnóstico já executado

Os comandos abaixo **já foram utilizados** durante a identificação elétrica e servem como registro do que foi validado. Não os execute automaticamente; analise se alguma informação deles precisa apenas ser representada pela API `libgpiod` no código:

```bash
gpiodetect
gpioinfo
pinctrl get 9-11,13-15,17,19-22,26-27

sudo pinctrl set 9-11,13-15,17,19-22,26-27 ip pn
sudo pinctrl set 10,9,11,17,27,22 ip pd

gpiomon -c gpiochip0 --bias=pull-down --edges=both 10 9 11 17 27 22
```

Durante testes isolados, uma coluna foi colocada como saída HIGH, por exemplo:

```bash
sudo pinctrl set 19 op dh pn
```

Isso foi usado somente para confirmar eletricamente uma coluna contra todas as linhas. No programa definitivo, faça a varredura com a API do `libgpiod`, ativando uma única coluna por vez.

Também foi usado este comando para devolver todas as GPIOs ao estado seguro:

```bash
sudo pinctrl set 9-11,13-15,17,19-22,26-27 ip pn
```

No software definitivo, o equivalente deve acontecer no encerramento usando a própria requisição do `libgpiod`.

## Trabalho solicitado

1. Localize o arquivo correto.
2. Leia todo o código relacionado à matriz e GPIO antes de editar.
3. Identifique o que precisa ser substituído, preservado ou removido.
4. Atualize a pinagem, direção das GPIOs, pulls, varredura, debounce e mapeamento de keycaps.
5. Elimine mapeamentos antigos incompatíveis.
6. Não confunda números BCM, pinos físicos e offsets do `gpiochip`.
7. Garanta que somente uma coluna seja saída por vez.
8. Garanta a liberação segura das GPIOs ao sair.
9. Faça validações estáticas e testes com abstrações ou mocks quando possível, sem depender de pressionamentos físicos.
10. Ao finalizar, informe claramente:
   - quais arquivos foram alterados;
   - como a varredura ficou implementada;
   - quais comportamentos antigos foram preservados;
   - como iniciar o programa;
   - quais testes foram realizados;
   - qualquer limitação ou conflito encontrado.

Não apenas explique a mudança: faça as alterações necessárias no código disponível nesse ambiente.