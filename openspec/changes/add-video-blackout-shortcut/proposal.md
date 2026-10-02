## Why

O produto é uma calculadora para quem **não depende da tela**: a voz é o canal principal (RF-04, RNF-02) e a entrada é o teclado físico (RF-05). Hoje, porém, **não existe forma de apagar a tela** — o LCD embutido fica aceso durante toda a sessão mesmo para um utilizador cego, que não tira nenhum proveito dele.

Isso custa duas coisas. **Autonomia:** o painel é uma carga permanente sobre o UPS HAT, cuja bateria é explicitamente limitada (§11, RF-06) — luz que ninguém olha é bateria desperdiçada. **Privacidade e conforto:** a expressão em curso e o resultado ficam visíveis a quem estiver por perto, e num ambiente escuro (sala de aula, quarto partilhado) o painel incomoda terceiros sem servir ao dono.

O interruptor físico do LCD (§7.0) **não** resolve: ele age só no LCD, é uma peça mecânica fora do alcance do software, e o PRD §7.4 trata o seu desligamento como *ausência de vídeo utilizável* — o app cai para `AUDIO_ONLY` e **destrói o front**, perdendo a UI e o modelo de interação por teclas. Não há nada equivalente para o monitor externo, e nada que o utilizador consiga acionar sem tirar a mão do teclado.

O RF-04 já prevê exatamente este estado — «operar em modo somente áudio quando o display estiver **desligado** ou indisponível» — mas hoje só o alcançamos por acidente de hardware, nunca por comando do utilizador.

## What Changes

- **Novo comando de teclado: apagar/religar as telas.** Um atalho alterna (*toggle*) entre `aceso` e `apagado`. Ao apagar, **todas** as saídas de vídeo do X são desligadas via `xrandr --off`: o LCD (HDMI0) e também o monitor externo (HDMI1) **quando estiver conectado**. Ao religar, a saída volta a ser escolhida pela regra de prioridade já existente do PRD §7.2 (monitor > LCD) — o comando não fixa painel nenhum.
- **A calculadora continua a funcionar, inteira, com as telas apagadas.** O front (janela Tk) **não** é destruído: continua a receber teclas, a calcular e a anunciar por voz. Esta é a diferença essencial em relação ao `DisplayMode.AUDIO_ONLY`, que existe para *ausência de hardware de vídeo* e troca o front por um laço de linha de comando. Apagar a tela é uma **preferência do utilizador**, não uma mudança de modo — expressão em curso, `Ans`, histórico e o estado graus/radianos ficam intactos.
- **Atalho `Ctrl` + `AC`, com teclas que já existem na matriz.** A matriz 6x7 real **não tem** tecla livre para o comando (a `?` que constava de `keypad.py` e dos ficheiros KLE não existe no teclado físico). O comando passa a ser a **função secundária de `AC`** com `Ctrl` — o mesmo modelo do `Ctrl` + `Ans` do histórico: não desloca nenhuma função científica do §5, não exige alteração de PCB, e é **o mesmo atalho no PC** (`Ctrl` e depois `Esc`). `AC` é a tecla de «voltar ao neutro», e sozinha continua a ser a via de recuperação (ver abaixo).
- **Confirmação por voz obrigatória, em ambos os sentidos.** Com a tela apagada o utilizador não tem retorno visual nenhum: o anúncio é a **única** prova de que o comando funcionou e a única forma de descobrir como desfazer. O anúncio de desligamento inclui a tecla que religa.
- **Anti-armadilha: `AC` sempre religa.** A tecla `AC` (`Esc` no PC), que já significa «volta ao estado neutro», passa a religar a tela quando ela está apagada. Sem isto, um utilizador vidente que acione o comando por engano fica perante um aparelho aparentemente morto — o modo mais grave de falha que esta mudança pode introduzir.
- **A escolha sobrevive à troca de painel (RF-09).** Se um monitor for ligado ou desligado com as telas apagadas, o `VideoOutputWatch` continua a fazer a entrega entre fronts, mas o novo front **nasce apagado**: uma reconfiguração de hardware não deve cancelar em silêncio uma escolha explícita do utilizador.
- **Novo código de aviso `WRN-013`** registado no PRD §13, como a própria secção exige para códigos novos. **Não** se reusa o `WRN-012`: ele já designa a *troca automática de saída* do RF-09, e dar duas leituras opostas à mesma frase quebraria a regra «mesmo código → mesmo significado» das convenções do projeto.
- **Documentação:** `docs/guias/comandos-teclado.md` deixa de listar `?` como tecla reservada (ela não existe na matriz) e passa a descrever o comando `Ctrl` + `AC`; o `README.md` da imagem Alpine ganha o caso na checklist de bring-up. Os ficheiros KLE não são alterados por esta mudança.

## Capabilities

### New Capabilities
- `video-blackout`: apagar e religar, por comando do utilizador, **todas** as saídas de vídeo reconhecidas, mantendo o front ativo e a calculadora plenamente operável por teclado e voz; inclui a confirmação falada, a via de recuperação garantida (`AC`) e a persistência da escolha ao longo da sessão.

### Modified Capabilities
(nenhuma.) O `display-switching` foi examinado e **não** muda ao nível de requisito: os seus requisitos descrevem o resultado de `DisplaySelector.current_mode()` e qual front é instanciado, e o blackout não toca em nenhum dos dois — a prioridade monitor > LCD continua a decidir qual painel *seria* usado, e continua a nascer exatamente um front por modo. A interação real (com o blackout ativo, a entrega de front do RF-09 tem de propagar o estado em vez de o descartar) é comportamento **da nova capacidade**, e fica especificada nela.

## Impact

- **Código alterado:** `software/hw_platform/video_output.py` (função para desligar todas as saídas e reler o estado para confirmar), `software/app.py` (`point_x_at` respeita o blackout; o estado acompanha o laço `run_mode`), `software/ui/hdmi/app.py` e `software/ui/lcd/app.py` (ligação da tecla e anúncio — mesmo comportamento nos dois fronts), `software/ui/shared/keypad.py` (`AC` ganha a função secundária `BLACKOUT`; a `?` inexistente sai do catálogo), `software/ui/shared/video_watch.py` (propagação do estado na entrega).
- **Sem alteração:** `software/core/` — o motor de cálculo não sabe que existe tela, e continua assim (regra do projeto); `software/hw_platform/display.py`, cuja regra de prioridade do §7 já está correta; o catálogo matemático do PRD §5.
- **Documentação alterada:** `docs/produto/PRD.md` §13 (registo do `WRN-013`), `docs/guias/comandos-teclado.md`, `system/rpi-os/alpine/README.md`.
- **Testes novos** em `software/tests/`, seguindo o padrão de `test_video_output.py`: o caminho `xrandr` é *mockado*, de modo que a suíte continua a correr sem servidor X no CI (Python 3.11).
- **Requisitos cobertos:** RF-04 (o «display desligado» que o requisito já previa passa a ser alcançável por comando), RF-05 (mapeamento de teclas documentado), RF-06 (autonomia do UPS), RF-09 e RNF-03 (a escolha atravessa o hotplug sem travar o app).
- **Risco principal:** deixar o utilizador sem forma de religar. Mitigado pelo anúncio falado que nomeia a tecla, pelo `AC` como via de recuperação e pelo facto de o estado nunca sobreviver a um reinício.

## Não-objetivos

- **Não** alterar o escopo matemático do PRD §5 nem o catálogo de funções: `AC` não tinha função com `Ctrl`, e o atalho não desloca nenhuma operação existente.
- **Não** acrescentar teclas à matriz nem alterar a PCB ou os ficheiros KLE.
- **Não** acoplar `software/core/` a `xrandr`, a Tk ou a qualquer noção de tela.
- **Não** substituir nem replicar o interruptor físico do LCD (§7.0), que continua a ser a via de hardware e a ser lido como ausência de vídeo.
- **Não** redefinir a prioridade monitor > LCD do §7.2, nem introduzir espelhamento ou uso simultâneo das duas telas.
- **Não** implementar economia de energia automática (apagar por inatividade, temporizador, ou reação ao nível de bateria do UPS): esta mudança entrega apenas o comando explícito. O gancho automático fica para uma mudança futura, se o TCC o justificar.
- **Não** persistir a preferência entre encerramentos — alinhado ao RF-13 e ao RF-06, que dispensam persistência de sessão. O aparelho arranca sempre com a tela acesa.
- **Não** desligar a **retroiluminação** do painel por GPIO/DSI nem cortar energia do monitor: o alcance é o CRTC do servidor X, que é o que o software controla de forma portável.
