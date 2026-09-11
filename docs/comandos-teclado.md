# Comandos especiais da calculadora

Referência dos **comandos que não são apenas "digitar um símbolo"**: modificadores (`Ctrl` / `Shift`), histórico, última resposta, limpar/apagar, alternância graus/radianos e apagar/religar as telas — tanto no **teclado comum de PC** (desenvolvimento e testes) como no **teclado físico** da calculadora (matriz 6x7 do TCC).

Fonte da verdade no código: [software/ui/shared/keypad.py](../software/ui/shared/keypad.py) (catálogo de teclas e funções secundárias), [software/hw_platform/keyboard.py](../software/hw_platform/keyboard.py) (mapa PC → token) e os `_bind_keyboard()` dos dois fronts ([lcd](../software/ui/lcd/app.py), [hdmi](../software/ui/hdmi/app.py)).

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
| `Ctrl` depois `Esc` | **Apagar/religar telas** | O mesmo `Ctrl` + `AC` da matriz (ver [§3](#apagar-e-religar-as-telas-ctrl--ac)). **No Windows, pressione em sequência** (solte o `Ctrl` antes do `Esc`): `Ctrl`+`Esc` juntos abrem o menu Iniciar |
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

## 3. Comandos especiais — teclado físico

O teclado do TCC tem as teclas dedicadas que faltam no PC. Layout visual: [docs/keyboard-layout](keyboard-layout/README.md) (ficheiro KLE).

| Tecla | Sozinha | Com `Ctrl` | Com `Shift` |
| ----- | ------- | ---------- | ----------- |
| `Ans` | resposta anterior | **Histórico** | — |
| `=` | calcula | **Última resposta** (repete o resultado completo, sem recalcular) | **Última resposta** |
| `/` | divisão | — | **RAD/DEG** (alterna graus ↔ radianos) |
| `.` | ponto decimal | — | `,` (vírgula) |
| `AC` | limpa tudo (e **religa** as telas, se estiverem apagadas) | **Apaga / religa todas as telas** (não limpa a expressão) | — |
| `Del` | apaga o último item | — | — |
| `Ctrl` | liga/desliga `CTRL` | — | — |
| `Shift` | liga/desliga `SHIFT` | — | — |

### Funções secundárias (`Ctrl` + tecla)

| Tecla | Sozinha | Com `Ctrl` |
| ----- | ------- | ---------- |
| `Pol` | `polar(` — polar → retangular | `rect(` — retangular → polar |
| `Pi` | `π` | `e` (número de Euler) |
| `sen` | `sen(` | `asin(` — arco seno |
| `cos` | `cos(` | `acos(` — arco cosseno |
| `tan` | `tan(` | `atan(` — arco tangente |
| `log` | `log(` — log decimal | `ln(` — log natural |
| `nCr` | `nCr(` — combinação | `nPr(` — permutação |
| `AC` | limpa tudo | **Apaga / religa as telas** |

Sem função secundária: `x!`, `x⁻¹`, `^`, `√`, `exp`, `(`, `)`, `%`, `e`, `Del`, dígitos e `+ - *`.

> Os exports KLE do layout ainda mostram uma tecla `?`; ela **não existe** na matriz 6x7 real e não tem função no software.

### Apagar e religar as telas (`Ctrl` + `AC`)

A calculadora não depende da tela (RF-04): para quem não a usa, um painel aceso só gasta bateria do UPS e expõe a conta a quem estiver por perto. **`Ctrl` e depois `AC` desliga todas as saídas de vídeo** — o LCD e também o monitor externo, se estiver ligado — e repetir o atalho religa.

| Ação | Teclado físico | Teclado de PC |
| ---- | -------------- | ------------- |
| **Apagar** as telas | `Ctrl`, depois `AC` | `Ctrl`, depois `Esc` |
| **Religar** as telas | `AC` (ou `Ctrl`, depois `AC` de novo) | `Esc` (ou `Ctrl`, depois `Esc`) |

- **Por que `Ctrl` + `AC`:** a matriz não tem tecla livre, então o comando é a função secundária de `AC` — o mesmo modelo do `Ctrl` + `Ans` do histórico, e o mesmo atalho no PC e no hardware. Como toda função secundária, **não limpa a expressão** e **consome o `Ctrl`**.
- **No Windows**, `Ctrl`+`Esc` pressionados **juntos** abrem o menu Iniciar. O `Ctrl` da calculadora é fixo (§1), então basta apertar `Ctrl`, soltar, e depois `Esc`. No aparelho (kiosk no Raspberry Pi) não há esse conflito.
- **A calculadora continua a funcionar inteira** com as telas apagadas: as teclas chegam, os resultados são calculados e anunciados, e a expressão em curso, o `Ans`, o histórico e o modo graus/radianos ficam intactos. Não é o modo somente áudio (§7).
- **Confirmação por voz, sempre** (aviso **WRN-013**, PRD §13): «Aviso 013. Telas desligadas. Para religar, pressione AC.» Ao religar, a voz diz em que painel a tela voltou. Se o comando falhar, a voz diz que **não** foi possível — nunca anuncia um desligamento que não aconteceu.
- **`AC` sozinho religa.** Quem apagar as telas por engano não fica diante de um aparelho aparentemente morto: `AC` (`Esc` no PC) religa as telas e depois limpa a expressão, como de costume. Com as telas acesas, `AC` não mexe no vídeo.
- **Ao religar vale a prioridade de sempre** (§7.2 do PRD): monitor externo se estiver ligado, senão o LCD. Um monitor ligado ou desligado durante o apagão é respeitado, e se ele chegar com as telas apagadas, a UI passa para ele **ainda apagada**.
- **Não é guardado**: a calculadora arranca sempre com a tela acesa.
- No modo "o que faz esta tecla?" (§4, só HDMI), `AC` é apenas **descrito**: «Função limpar tudo. Com Controle ativo, função desligar ou religar as telas.»

### Funções alternativas (`Shift` + tecla)

| Tecla | Com `Shift` |
| ----- | ----------- |
| `log` | `logbase(` — logaritmo numa base qualquer |
| `/` | **RAD/DEG** |
| `.` | `,` |
| `=` | **Última resposta** |

---

## 4. `Ctrl` + `Shift` juntos — modo "o que faz esta tecla?" (só HDMI)

Com **os dois** indicadores acesos, a próxima tecla **não é executada**: a voz descreve as três funções dela. Exemplo, ao pressionar `log`:

> «Função logaritmo decimal. Com Controle ativo, função logaritmo natural. Com Shift ativo, função logaritmo na base x.»

Serve para explorar o teclado sem medo de estragar a expressão em curso. Implementado no front HDMI ([hdmi/app.py](../software/ui/hdmi/app.py)); o front LCD ainda não tem este modo.

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

- **O teclado físico ainda não está ligado ao software.** [KeyboardAdapter](../software/hw_platform/keyboard.py) é hoje um adaptador do teclado de PC; a leitura da matriz por GPIO está pendente. As teclas, tokens e atalhos desta página já estão fixados para que essa ligação não mude o comportamento.
- **No PC, `Ctrl` + tecla só funciona com `a` (`Ans`) e `Esc` (`AC`).** As demais funções secundárias dependem de teclas que só existem na matriz física — no HDMI, use os botões na tela com o `CTRL` ligado (os rótulos mudam para a função secundária).
- **`Ctrl` + `Enter` não faz "última resposta"** no PC: `Enter` entra como `=` puro, sem função secundária. Use o botão `=` na tela com o `CTRL` ligado.
- **Símbolos que exigem `Shift` no PC** (por exemplo `(`, `)`, `*`, `^` em teclados ABNT/US) acendem o indicador `SHIFT`, porque o front trata `Shift` como comando. O símbolo é inserido normalmente, mas o indicador pode ficar aceso — pressione `Shift` uma vez para o desligar.
- **`Ctrl` + `Esc` juntos no Windows abrem o menu Iniciar** em vez de apagar as telas: pressione `Ctrl`, solte, e depois `Esc`.
- **Apagar as telas atua no servidor X** (`xrandr --off`): fora do Raspberry Pi, sem X, o comando é registado no log e a voz avisa que não foi possível desligar — a calculadora segue normal. Se o painel corta a retroiluminação sem sinal ou mostra «sem sinal» aceso depende do hardware e fica por confirmar na checklist da imagem.

---

## Ver também

- [README.md](../README.md) — como executar e forçar cada front
- [PRD.md](../PRD.md) §5 (catálogo de funções), §7 (saídas de vídeo), §13 (códigos de erro)
- [docs/keyboard-layout/README.md](keyboard-layout/README.md) — layout físico no formato KLE
