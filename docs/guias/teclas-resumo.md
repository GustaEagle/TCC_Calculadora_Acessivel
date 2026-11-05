# Resumo das teclas (consulta rápida)

Folha de consulta do **teclado físico** da calculadora. Para o detalhe completo —
posição elétrica de cada tecla, varredura da matriz, diagnóstico de hardware —
veja [teclado-matriz.md](teclado-matriz.md), que é a referência.

**38 teclas** numa matriz **6×7** (4 posições sem switch).

---

## O essencial antes de tudo

`Ctrl` e `Shift` são **toggle, não de segurar**: pressione o modificador, solte, e
depois a tecla. O indicador acende na tela e a voz confirma. O modificador
desliga-se sozinho ao ser usado.

> Isto é decisão de acessibilidade: quem opera com uma mão só, ou sem ver a tela,
> não consegue segurar duas teclas ao mesmo tempo.

Se não souber um atalho, pressione **`?`** — a voz anuncia o modo angular e todos
os atalhos. É a única forma de descobri-los sem olhar para a tela.

---

## Dígitos e operadores

`0`–`9` · `+` `-` `*` `/` · `^` · `%` · `(` `)` · `=`

A tecla impressa `,` produz **`.`** (ponto decimal) sozinha e **`,`** (vírgula,
separador de argumentos) com `Shift`.

## Funções científicas

| Sozinha | Com `Ctrl` | Com `Shift` |
| ------- | ---------- | ----------- |
| `sen(` `cos(` `tan(` | `asin(` `acos(` `atan(` | — |
| `log(` | `ln(` | `logbase(` |
| `π` | `e` | — |
| `e` (Euler) | `EXP` (×10ˣ) | — |
| `Pol(` → para polar | `Rec(` → para retangular | — |
| `nCr` | `nPr` | — |
| `!` `inv(` `sqrt(` | — | — |

## Teclas de controle

| Tecla | Sozinha | Com `Ctrl` | Com `Shift` |
| ----- | ------- | ---------- | ----------- |
| `Ans` | resposta anterior | **histórico** | **lê a expressão** |
| `=` | calcula | última resposta | última resposta |
| `AC` | limpa tudo | **apaga / religa as telas** | — |
| `Del` | apaga o último item | — | — |
| `/` | `/` | — | **RAD ↔ DEG** |
| `+` `-` | operadores | **volume + / −** | — |
| `,` | `.` decimal | — | `,` separador |
| `?` | **consulta de tecla** | — | — |
| `exp` (keycap) | liga/desliga `SHIFT` | — | — |
| `Shift` (keycap) | **RAD ↔ DEG** | — | — |

> **Os keycaps `exp` e `Shift` não fazem o que está impresso neles.** Com a
> tecla `EXP` realojada no `Ctrl` da tecla `e`, a tecla impressa `exp` ficou
> livre e assumiu o `Shift`; a impressa `Shift` assumiu o RAD/DEG. Troque os
> dois keycaps de posição no hotswap para a legenda voltar a bater com a função.

> **`Pol` e `Rec` dizem o destino da conversão.** `Pol(x,y)` devolve
> `(r, ângulo)` e `Rec(r,ângulo)` devolve `(x, y)` — como numa Casio. Os dois
> valores aparecem em **duas linhas** na tela. **`EXP` é expoente de base dez**
> (`3 EXP 8` = 3×10⁸); a exponencial de Euler é `e` `^` `x`.

---

## Quatro coisas que surpreendem

**`nCr` fica entre os números**, como numa científica de verdade:
`5` `nCr` `2` `=` → `10`. A forma `nCr(5,2)` **não** é aceita (devolve `ERR-007`).
Para permutação: `5` `Ctrl` `nCr` `2` `=` → `20`.

**`AC` sozinho religa as telas.** Se apagou o vídeo com `Ctrl` + `AC` e o aparelho
parece morto, `AC` traz a imagem de volta — e só depois limpa a expressão.

**`Ctrl` + `Shift` juntos** entram no modo *"o que faz esta tecla?"*: a próxima
tecla **não é executada**, a voz apenas descreve as três funções dela. Só existe
no front do monitor externo.

**Depois de um `=`**, a mesma tecla faz coisas diferentes: um **operador**
continua a conta a partir do resultado (`Ans` + operador); um **dígito ou função**
começa uma expressão nova, limpando a anterior.

---

## Funções binárias precisam da vírgula

As conversões de coordenadas levam dois argumentos, e aí entra o `Shift` na tecla
do ponto:

| Quero | Pressiono |
| ----- | --------- |
| `polar(5,2)` | `Pol` `5` `Shift` `,` `2` `)` |
| `rect(5,30)` | `Ctrl` `Pol` `5` `Shift` `,` `30` `)` |

---

## Ver também

- [teclado-matriz.md](teclado-matriz.md) — referência completa: posição de cada
  tecla, leitura da matriz, limitações e diagnóstico
- [comandos-teclado.md](comandos-teclado.md) — os mesmos comandos no **teclado de
  PC** (desenvolvimento e testes)

> As funções acima vêm de `software/ui/shared/keypad.py`, e as posições de
> `software/hw_platform/keypad_pinout.py`. Se o código mudar, este resumo e a
> referência ficam desatualizados — foi o que aconteceu com três atalhos
> (volume e "ler a expressão"), que existiam no código e faltavam na tabela.
