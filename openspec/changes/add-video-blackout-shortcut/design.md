## Context

Ver `proposal.md` — Why para a motivação, e `specs/video-blackout/spec.md` para os requisitos.

O que já existe e condiciona a abordagem:

- **`hw_platform/video_output.py`** já sabe falar com o `xrandr`: descobre os nomes reais das saídas (`read_outputs()`), aplica um layout exclusivo numa única chamada (`activate()`) e **relê o estado para confirmar** que o CRTC mudou, porque o código de saída do `xrandr` só diz que o comando foi aceite. Tudo é melhor-esforço: fora do Pi não há X e as chamadas reportam falha em vez de levantar exceção.
- **`app.py:run_mode()`** é um laço: `point_x_at(mode)` → `start_front(mode, state, speech)`. O front devolve o modo que assume a seguir (ou `None` para sair). O `CalculatorState` é construído **uma vez** e atravessa todas as trocas de front — é assim que a expressão em curso sobrevive ao RF-09.
- **`ui/shared/video_watch.py`** faz a entrega: sonda o *sysfs* de 2 em 2 segundos e, ao detetar mudança, destrói a janela para que o laço construa o outro front.
- **`ui/shared/keypad.py`** listava uma tecla `?` com token vazio, mas **ela não existe na matriz 6x7 real** — não há tecla livre. `AC` e `Del` são as teclas de controlo sem função secundária com `Ctrl`, e o `Ctrl` + `Ans` do histórico já estabeleceu o modelo «comando = modificador + tecla existente».
- Os dois fronts (`ui/lcd`, `ui/hdmi`) têm `_bind_keyboard()` e `_handle_token()` deliberadamente espelhados.

Restrição decisiva: `xrandr --off` desativa o **CRTC**, não o conector. O *sysfs* continua a reportar `connected`, logo o `DisplayWatcher` **não** vê o blackout como mudança de vídeo e não dispara entrega de front. Isto é o que torna a funcionalidade possível sem tocar na máquina de estados do §7.4.

## Goals / Non-Goals

**Goals:**
- Manter o blackout **inteiramente fora** de `DisplayMode`, para que a máquina de estados do PRD §7.4 continue a significar exatamente «que hardware de vídeo existe».
- Um único ponto que aplica vídeo ao servidor X, para que acender e apagar não possam divergir.
- Comportamento idêntico nos dois fronts sem duplicar lógica — mesma regra que já pôs `video_watch.py` em `ui/shared/`.
- Testável no CI sem servidor X, pelo mesmo padrão de *mock* de `test_video_output.py`.

**Non-Goals:**
- **Não** usar DPMS (`xset dpms force off`): o DPMS reacende a qualquer evento de input, e num aparelho cujo único meio de interação é o teclado a tela reacenderia na tecla seguinte. É a razão técnica pela qual o alcance é o CRTC.
- **Não** desligar retroiluminação por GPIO/DSI nem cortar energia do monitor.
- **Não** acrescentar opção de linha de comando para arrancar apagado — contraria o requisito de arranque sempre aceso.

## Decisions

### D1 — O blackout é estado de sessão, não um `DisplayMode`

**Escolha:** um objeto de sessão mutável, criado em `run_mode()` e passado a `point_x_at()` e a cada front.

**Alternativa rejeitada — `DisplayMode.BLACKOUT`:** `DisplayMode` decide **qual front construir**. Um valor novo obrigaria `start_front()` a escolher um front para um estado que não tem front próprio, e a entrega do RF-09 passaria a ter de distinguir «mudou o hardware» de «o utilizador carregou numa tecla». Pior: `AUDIO_ONLY` troca o front pelo `AudioOnlyCalculator`, que lê **linhas inteiras** do stdin — um modelo de interação completamente diferente do teclado tecla-a-tecla. Reaproveitá-lo destruiria a expressão em curso e mudaria o significado de cada tecla.

**Alternativa rejeitada — guardar em `CalculatorState`:** viola a regra do projeto de manter `core/` sem qualquer noção de UI ou de vídeo.

**Alternativa rejeitada — global de módulo em `video_output`:** invisível nos testes, e obrigaria a limpeza entre casos.

Como o objeto pertence ao laço `run_mode()`, a persistência através da troca de front (RF-09) sai **de graça**: é o mesmo mecanismo que já preserva o `CalculatorState`, e não há estado a serializar.

### D2 — Um único ponto aplica o vídeo

`point_x_at()` passa a consultar o estado de sessão: apagado → desliga todas as saídas; aceso → mantém o comportamento atual (`activate()` no painel escolhido pela prioridade do §7.2). O *toggle* nos fronts apenas inverte o sinalizador e chama esse mesmo ponto.

Consequência desejada: o reacendimento **não** precisa de recordar qual painel estava aceso. Ele reexecuta a regra de prioridade, e por isso um monitor ligado ou removido durante o blackout é automaticamente respeitado — sem código adicional.

### D3 — Desligar tudo numa só chamada, e verificar

`xrandr --output <A> --off --output <B> --off` numa única invocação, pela mesma razão que `activate()` já documenta: o servidor reconfigura uma vez em vez de piscar entre dois comandos. A seguir, relê `read_outputs()` e confirma que **nenhuma** saída ficou ativa — o código de saída do `xrandr` diz que o comando foi aceite, não que o CRTC obedeceu.

Os nomes das saídas vêm de `read_outputs()`/`output_name()`, que já resolvem a divergência `HDMI-A-1` (sysfs) vs `HDMI-1` (driver X) na ordem env var → saída presente no X → convenção. Nada de nomes adivinhados.

### D4 — `Ctrl` + `AC`, igual na matriz e no PC

**Escolha:** `BLACKOUT` é a função secundária (`Ctrl`) da tecla `AC`. Na matriz: `Ctrl` e depois `AC`. No PC: `Ctrl` e depois `Esc` (o `Esc` já é o `AC`).

**Porquê `AC`:** é a tecla de «voltar ao estado neutro», e **sozinha** continua a ser a via de recuperação (D5). Quem apaga por engano recupera com a tecla ao lado do dedo, sem precisar de lembrar o modificador. Como toda a função secundária, `Ctrl` + `AC` **substitui** a primária — não limpa a expressão — e consome o `Ctrl`.

**Porquê não outra:** a matriz não tem tecla livre (a `?` do catálogo antigo não existe no hardware). `Ctrl` + `Del` funcionaria, mas separaria o atalho da via de recuperação em teclas diferentes; `Shift` + `AC` fica livre para o futuro. `Ctrl` + `Shift` + tecla está tomado pelo modo «o que faz esta tecla?», que continua a apenas **descrever** `AC` e as suas duas funções.

**Teclado de PC:** o teclado chega ao `_handle_token()` sem o `secondary` da definição da tecla — o mesmo problema que o `Ans` já resolve atribuindo `HISTORY` quando vem vazio. `AC` recebe o mesmo tratamento. Não há atalho extra no PC (`v`, `<question>`): o comando é o mesmo nos dois teclados, como o do histórico. No Windows, `Ctrl`+`Esc` *em simultâneo* abre o menu Iniciar; como o `Ctrl` da calculadora é fixo, pressiona-se em sequência — o kiosk do Pi não tem esse conflito.

**Nome falado:** o anúncio de desligamento nomeia **`AC`** como a tecla que religa (a mais curta das duas vias, e a mesma no PC como `Esc`).

### D5 — `AC` como via de recuperação, em código partilhado

A regra «`AC` reacende antes de limpar» vive num módulo novo `ui/shared/video_blackout.py`, junto com o objeto de sessão e as frases do `WRN-013`. Os fronts chamam-no de `_handle_token()`. Mesma justificação que pôs `video_watch.py` em `ui/shared/`: um só comportamento para os dois fronts, e testável com um duplo em vez de uma janela real.

### D6 — `WRN-013` novo, em vez de reusar `WRN-012`

O PRD §13 exige que códigos novos sejam registados na secção. `WRN-012` designa a **troca automática** de saída do RF-09 e é anunciado como «Saída de vídeo alterada» — o próprio `video_output._warn_layout()` já documenta a recusa em dar dois sentidos à mesma frase. Um comando deliberado do utilizador é outro evento e recebe outro código.

### D7 — Dimensionamento da janela durante o blackout

O front HDMI dimensiona-se por `video_output.screen_size()`. Com todos os CRTC desligados, o ecrã X pode reportar um tamanho degenerado, e uma reconstrução de front durante o blackout (hotplug) escolheria a faixa de layout errada. Mitigação: durante o blackout, o dimensionamento usa o modo **preferido da saída-alvo** em vez do tamanho corrente do ecrã, caindo para o comportamento atual quando o valor não for legível.

## Risks / Trade-offs

- **O driver recusa desligar o último CRTC ativo** → `activate()` já tem o padrão de verificação: se a releitura mostrar saída ainda ativa, o comando é reportado como falhado, registado, e o estado de sessão **não** é invertido — a tela continua acesa e o anúncio não mente. Contingência, se acontecer no hardware: manter um CRTC ativo apontado para uma saída sem modo visível. Fica por confirmar no bring-up (secção de verificação em hardware de `tasks.md`).
- **Sem CRTC ativo, as teclas deixam de chegar à janela Tk** → seria uma falha total: nem o *toggle* nem o `AC` de recuperação funcionariam. Em X o foco de input é independente da configuração de saída, e a janela continua mapeada e focada, portanto o esperado é que funcione; mas é a hipótese que sustenta toda a funcionalidade e **tem de ser verificada no hardware antes de fechar a mudança**.
- **O utilizador vidente aciona por engano e julga o aparelho avariado** → tripla defesa: anúncio falado que nomeia a tecla de retorno, `AC` como segunda via, e ausência de persistência (reiniciar resolve sempre).
- **Perda de autonomia menor do que o esperado** → desligar o CRTC não garante que o painel corte a retroiluminação; alguns painéis entram em standby por ausência de sinal, outros mostram «sem sinal» iluminado. O ganho de bateria é uma expectativa a medir, não uma garantia — a privacidade e o conforto, esses, são obtidos em qualquer caso.
- **Divergência entre os dois fronts** → mitigada por D5 (lógica em `ui/shared/`), mas a ligação da tecla continua a ser duplicada em cada `_bind_keyboard()`, como já acontece com `Return`/`Escape`. Aceite: seguir o padrão existente vale mais do que introduzir um mecanismo novo só para esta tecla.

## Migration Plan

Sem migração de dados nem alteração de contrato: a funcionalidade é aditiva e o estado inicial é o comportamento atual (tela acesa). Reversão = reverter o commit; nada persiste que sobreviva a isso.

Ordem de entrada: mecânica em `video_output` (com testes *mockados*) → estado de sessão e ligação em `app.py` → tecla e anúncio nos fronts → documentação e registo do `WRN-013` → verificação no hardware.

## Open Questions

- **Frase exata do `WRN-013`.** Precisa de ficar registada no PRD §13, mas a redação pode ser afinada depois de ouvida em voz pt-BR sem alterar spec, abordagem ou tarefas.
- **Se o ganho de autonomia justifica um gancho automático** (apagar por inatividade, ou ao entrar em bateria baixa pelo UPS). Fica explicitamente fora desta mudança; a medição no hardware dirá se vale uma proposta futura.
