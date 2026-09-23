# Comandos especiais da calculadora

Referência dos **comandos que não são apenas "digitar um símbolo"** no **teclado comum de PC** (desenvolvimento e testes): modificadores (`Ctrl` / `Shift`), histórico, última resposta, limpar/apagar, alternância graus/radianos e apagar/religar as telas.

> **Procura o teclado do produto?** O catálogo completo da **matriz 6×7** — as 38 teclas, o layout da grade, a leitura por GPIO e o diagnóstico — está em **[teclado-matriz.md](teclado-matriz.md)**. Este documento cobre o teclado de PC e os conceitos comuns aos dois.

Fonte da verdade no código: [`hw_platform/keyboard.py`](../../software/hw_platform/keyboard.py) (mapa PC → token), [`ui/shared/keypad.py`](../../software/ui/shared/keypad.py) (catálogo de funções e nomes falados) e os `_bind_keyboard()` dos dois fronts ([lcd](../../software/ui/lcd/app.py), [hdmi](../../software/ui/hdmi/app.py)). Os módulos da matriz estão listados em [teclado-matriz.md](teclado-matriz.md).

---

## 1. Como funcionam `Ctrl` e `Shift`

Os modificadores são **fixos (toggle)**, não de pressionar-e-segurar:

1. Pressione `Ctrl` (ou `Shift`) — o indicador `CTRL` / `SHIFT` acende no topo da tela e a voz anuncia «Controle ativo» / «Shift ativo».
2. Pressione a tecla seguinte — ela executa a **função secundária**.
3. O modificador é **consumido automaticamente** (desliga sozinho) assim que uma tecla que tem função secundária é usada.

> Isto é uma decisão de acessibilidade: quem opera com uma mão só, ou sem enxergar a tela, não precisa segurar duas teclas ao mesmo tempo. Pressionar `Ctrl` de novo cancela («Controle desativado»).

Se a tecla pressionada **não tiver** função para o modificador ativo, ela age normalmente e o modificador **continua ligado** até ser usado ou cancelado.

---

## 2. Comandos especiais — teclado comum (PC)

Válido ao rodar `python software/app.py --force-mode hdmi` ou `--force-mode lcd`.

| Tecla no PC | Comando | Efeito |
| ----------- | ------- | ------ |
| `Enter` | `=` | Avalia a expressão e anuncia «Resultado …» |
| `Backspace` | `DEL` | Apaga o último caractere — funções (`sen(`, `log(`, `nCr(`, …) são apagadas como **bloco único** |
| `Esc` | `AC` | Limpa tudo (expressão e último resultado). Com as telas apagadas, **religa-as** antes de limpar |
| `Ctrl` (esq. ou dir.) | modificador | Liga/desliga o estado `CTRL` |
| `Shift` (esq. ou dir.) | modificador | Liga/desliga o estado `SHIFT` |
| `a` / `A` | `Ans` | Insere a resposta anterior — **substitui a tecla `Ans`** da matriz, que não existe no PC |
| `Ctrl` depois `Esc` | **Apagar/religar telas** | O mesmo `Ctrl` + `AC` da matriz (ver [§3](#apagar-e-religar-as-telas-ctrl-depois-esc)). **No Windows, pressione em sequência** (solte o `Ctrl` antes do `Esc`): `Ctrl`+`Esc` juntos abrem o menu Iniciar |
| `Ctrl` depois `a` | **Histórico** | LCD: abre/fecha o painel de histórico. HDMI: anuncia o histórico por voz (o painel já é permanente) |
| `Espaço` (com o foco no botão) | **Mostrar/Ocultar teclado** | Só no HDMI: o teclado na tela começa oculto e o botão do rodapé recebe o foco inicial — `Espaço` alterna. **Não** use `Enter` (está ligado ao `=`) |

### Símbolos aceites diretamente

| Teclas | Token gerado |
| ------ | ------------ |
| `0`–`9` | dígitos |
| `+` `-` `/` `^` | operadores |
| `x` / `X` / `*` | `*` (multiplicação) |
| `.` `,` | ponto decimal / vírgula |
| `(` `)` | parênteses |

**Qualquer outra tecla é ignorada.** As funções científicas (`sen`, `cos`, `log`, `√`, `nCr`, `exp`, `π`, `%`, …) **não têm atalho no teclado do PC**: no front HDMI use os botões na tela — o teclado começa **oculto** e é revelado pelo botão *Mostrar teclado* no rodapé (não há atalho de tecla para ele; com o teclado oculto o botão já vem focado, então `Espaço` alterna). No front LCD não há botões nem esse teclado na tela — ele é feito para o teclado físico.

---

## 3. Teclado físico (matriz 6×7)

O teclado do produto tem as teclas dedicadas que faltam no PC, e a matriz entra **pelo mesmo caminho** do teclado comum: modificadores, histórico, telas e anúncios de voz funcionam igual. O que muda é o alcance:

| | Teclado de PC | Matriz 6×7 |
| --- | ------------- | ---------- |
| Funções secundárias (`Ctrl`/`Shift`) | Só em `a` (`Ans`) e `Esc` (`AC`) | Em **todas** as teclas que têm uma |
| Funções científicas (`sen`, `log`, `√`, `nCr`, …) | Sem atalho — só pelos botões na tela (HDMI) | Tecla dedicada |
| `Ans` | Tecla `a` / `A` | Tecla dedicada |
| Apagar/religar telas | `Ctrl`, depois `Esc` | `Ctrl`, depois `AC` |
| Modo somente áudio | Funciona (linha digitada + `Enter`) | Não funciona |

**Referência completa da matriz:** [teclado-matriz.md](teclado-matriz.md) — catálogo das 38 teclas com posição `C#L#` e `SW#`, layout da grade, polaridade e debounce da varredura, bring-up e limitações. Layout visual: [keyboard-layout/](../keyboard-layout/README.md). Ligação elétrica: [pinout.md §6](../raspberry-pi-4b/pinout.md).

### Apagar e religar as telas (`Ctrl` depois `Esc`)

A calculadora não depende da tela (RF-04): para quem não a usa, um painel aceso só gasta bateria do UPS e expõe a conta a quem estiver por perto. **`Ctrl` e depois `Esc` desliga todas as saídas de vídeo** — o LCD e também o monitor externo, se estiver ligado — e repetir o atalho religa. É o mesmo comando que na matriz é `Ctrl` + `AC`.

| Ação | Teclado de PC | Teclado físico |
| ---- | ------------- | -------------- |
| **Apagar** as telas | `Ctrl`, depois `Esc` | `Ctrl`, depois `AC` |
| **Religar** as telas | `Esc` (ou `Ctrl`, depois `Esc`) | `AC` (ou `Ctrl`, depois `AC`) |

- **No Windows**, `Ctrl`+`Esc` pressionados **juntos** abrem o menu Iniciar. O `Ctrl` da calculadora é fixo ([§1](#1-como-funcionam-ctrl-e-shift)), então basta apertar `Ctrl`, soltar, e depois `Esc`. No aparelho (kiosk no Raspberry Pi) não há esse conflito.
- **`Esc` sozinho religa.** Quem apagar as telas por engano não fica diante de um aparelho aparentemente morto: `Esc` religa e depois limpa a expressão, como de costume. Com as telas acesas, `Esc` não mexe no vídeo.
- **A calculadora continua a funcionar inteira** com as telas apagadas — expressão em curso, `Ans`, histórico e modo graus/radianos ficam intactos. Não é o modo somente áudio ([§7](#7-modo-somente-áudio)).
- **Confirmação por voz, sempre** (aviso **WRN-013**, PRD §13): «Aviso 013. Telas desligadas. Para religar, pressione AC.» Se o comando falhar, a voz diz que **não** foi possível — nunca anuncia um desligamento que não aconteceu.
- Razões de projeto, comportamento ao religar e prioridade entre painéis: [teclado-matriz.md §5](teclado-matriz.md#5-apagar-e-religar-as-telas-ctrl--ac).

---

## 4. `Ctrl` + `Shift` juntos — modo "o que faz esta tecla?" (só HDMI)

Com **os dois** indicadores acesos, a próxima tecla **não é executada**: a voz descreve as três funções dela. Exemplo, ao pressionar `log`:

> «Função logaritmo decimal. Com Controle ativo, função logaritmo natural. Com Shift ativo, função logaritmo na base x.»

Serve para explorar o teclado sem medo de estragar a expressão em curso. Implementado no front HDMI ([hdmi/app.py](../../software/ui/hdmi/app.py)); o front LCD ainda não tem este modo.

---

## 5. Histórico e última resposta

| Comando | O que faz |
| ------- | --------- |
| `Ctrl` + `Ans` | **Histórico**: os últimos cálculos **bem-sucedidos** (10 no HDMI, 6 no LCD), do mais recente para o mais antigo. No LCD abre um painel — qualquer outra tecla o fecha e volta ao display. |
| `Ctrl` + `=` ou `Shift` + `=` | **Última resposta**: reanuncia/reexibe o último resultado **completo** (sem o truncamento do display), sem recalcular e **sem tocar** na expressão que estiver a ser digitada. |
| `Ans` | Insere a resposta anterior **dentro** da expressão. |

Erros não entram no histórico mostrado/anunciado. Sem resposta anterior na sessão, a última resposta devolve o aviso **WRN-010** («Não há resposta anterior»).

**Não existe botão de histórico** — nem na tela, nem no teclado físico: o atalho `Ctrl` + `Ans` foi escolhido por usar só teclas que já existem na matriz 6x7, de forma que PC e hardware tenham exatamente o mesmo comando.

---

## 6. Encadeamento após um resultado

Não são teclas especiais, mas mudam o que a mesma tecla faz **logo depois de um `=` bem-sucedido**:

| Tecla seguinte | Comportamento |
| -------------- | ------------- |
| Operador (`+ - * / ^`) | Continua a partir do resultado: a expressão vira `Ans` + operador |
| Dígito, função, `π`, `e`, `Ans` | Começa uma expressão nova (limpa a anterior automaticamente) |
| Dois operadores seguidos | O segundo **substitui** o primeiro; a voz anuncia «Substituindo» |

---

## 7. Modo somente áudio

`python software/app.py --force-mode audio` não usa teclas isoladas: escreve-se a **expressão inteira** numa linha e pressiona-se `Enter`.

| Entrada | Efeito |
| ------- | ------ |
| `2+2` + `Enter` | Calcula e anuncia o resultado |
| `sair`, `quit` ou `exit` | Encerra |
| `Ctrl` + `C` | Encerra |

O mesmo mapa de símbolos do PC vale aqui (`x` → `*`, `a` → `Ans`, …).

---

## 8. Observações e limitações conhecidas

- **No PC, `Ctrl` + tecla só funciona com `a` (`Ans`) e `Esc` (`AC`).** As demais funções secundárias dependem de teclas que só existem na matriz física — no HDMI, use os botões na tela com o `CTRL` ligado (os rótulos mudam para a função secundária).
- **`Ctrl` + `Enter` não faz "última resposta"** no PC: `Enter` entra como `=` puro, sem função secundária. Use o botão `=` na tela com o `CTRL` ligado.
- **Símbolos que exigem `Shift` no PC** (por exemplo `(`, `)`, `*`, `^` em teclados ABNT/US) acendem o indicador `SHIFT`, porque o front trata `Shift` como comando. O símbolo é inserido normalmente, mas o indicador pode ficar aceso — pressione `Shift` uma vez para o desligar.
- **`Ctrl` + `Esc` juntos no Windows abrem o menu Iniciar** em vez de apagar as telas: pressione `Ctrl`, solte, e depois `Esc`.
- **Apagar as telas atua no servidor X** (`xrandr --off`): fora do Raspberry Pi, sem X, o comando é registado no log e a voz avisa que não foi possível desligar — a calculadora segue normal. Se o painel corta a retroiluminação sem sinal ou mostra «sem sinal» aceso depende do hardware e fica por confirmar na checklist da imagem.
- **Ligar/desligar a matriz e diagnosticar teclas** (`--keypad-matrix off`, `keypad_bringup.py`): [teclado-matriz.md §7](teclado-matriz.md#7-ligar-desligar-e-diagnosticar).

---

## Ver também

- [teclado-matriz.md](teclado-matriz.md) — **teclado físico do produto**: as 38 teclas, layout, GPIO e diagnóstico
- [README.md](../../README.md) — como executar e forçar cada front
- [PRD.md](../produto/PRD.md) §5 (catálogo de funções), §7 (saídas de vídeo), §13 (códigos de erro)
- [docs/keyboard-layout/README.md](../keyboard-layout/README.md) — layout físico no formato KLE
