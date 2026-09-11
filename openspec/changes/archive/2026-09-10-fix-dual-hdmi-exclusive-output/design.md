## Context

Ver `proposal.md` — Why para a motivação e o diagnóstico. Requisitos em `specs/video-output-exclusivity/spec.md`.

Restrições que moldam a abordagem:

- **A regra do §7 já existe e está certa.** `DisplaySelector.current_mode()` devolve `HDMI` quando as duas portas estão reconhecidas, com testes em `test_display_selector.py`. Nada nesta mudança redefine a prioridade — só a faz valer no servidor X.
- **A imagem não tem gerenciador de janelas.** O `.xinitrc` sobe `xset` + o app, nada mais. Não há nada entre o X e o Tk para posicionar ou maximizar janelas: a geometria é responsabilidade do próprio app.
- **`max_framebuffers=2` tem de ficar.** É o que permite a segunda porta ter framebuffer e, com `vc4-kms-v3d`, o que dá hotplug em `/sys/class/drm` — a base do RF-09. Qualquer solução que desligue a segunda porta no firmware quebra a deteção do monitor ligado em uso.
- **Os testes correm sem X.** O CI (Python 3.11, sem HDMI e sem `DISPLAY`) tem de continuar verde; todo caminho novo que toque no `xrandr` precisa de ser mockável, como já acontece em `test_video_output.py`.
- **O que o utilizador vê é a única prova.** No kiosk o tty1 fica coberto pelo X e não há como olhar para o stderr; hoje uma falha de `xrandr` é indistinguível de um sucesso.

## Goals / Non-Goals

**Goals:**

- Que o desktop estendido nunca chegue a ser visível, nem por um instante no boot.
- Que uma falha de reconfiguração seja detetada pelo próprio sistema, não pelo olho de quem está a testar.
- Que a resolução de nomes DRM → `xrandr` deixe de ser um palpite que falha em silêncio.
- Manter a decisão do §7 num único sítio (`display.py`), sem a duplicar em shell nem em `xorg.conf`.

**Non-Goals (nível de design; os de produto estão na proposta):**

- Não reescrever `DisplaySelector` nem `DisplayWatcher` — a deteção fica como está.
- Não introduzir dependência nova: `xrandr` já está implícito via `xorg-server`/`xinit`, e a leitura continua por `subprocess`, sem biblioteca de X.
- Não criar um daemon nem um serviço OpenRC próprio para vídeo; o app continua a ser o dono do estado de saída.
- Não persistir o layout entre arranques — ele é sempre rederivado do estado real das portas.

## Decisions

### D1. A exclusividade é aplicada pelo app, chamado pela sessão gráfica — não por `xorg.conf`

Novo modo `python3 -m software.app --apply-video-layout`: resolve o modo pelo `DisplaySelector`, aplica o layout, encerra. O `.xinitrc` chama-o entre o `xset` e o laço do app.

*Porquê:* é o único ponto onde a regra do §7 já vive. O X arranca, autoconfigura, e o comando corrige antes de existir qualquer janela — a janela de tempo em que o estendido existe fica reduzida a milissegundos sem nada desenhado por cima.

*Alternativas consideradas:*

- **`/etc/X11/xorg.conf.d/10-outputs.conf` estático** — descartada: um `xorg.conf` fixa o layout no arranque do X e não sabe exprimir "monitor se presente, senão LCD". Pior, congelaria o estado do boot e mataria o RF-09.
- **Lógica de prioridade em shell dentro do `.xinitrc`** — descartada: duplica o §7 em duas linguagens; a próxima alteração da regra passaria a ter de ser feita em dois sítios e um deles não tem testes.
- **Desligar a segunda porta no `usercfg.txt`** — descartada: quebra o hotplug do RF-09, como acima.

### D2. Os nomes de saída X são descobertos por `xrandr --query`, com a convenção como último recurso

`video_output` ganha uma leitura das saídas presentes no X. A precedência passa a ser: **variável de ambiente → saída presente no X que casa com o conector → convenção `drm_to_xrandr()`**.

O casamento normaliza os dois lados (minúsculas, sem hífenes) antes de comparar, para que `HDMI-A-2`, `HDMI-2`, `HDMI2` e `hdmi-2` sejam reconhecidos como a mesma porta.

*Porquê:* a convenção `HDMI-A-N` → `HDMI-N` é uma suposição sobre o driver `modesetting`, e é precisamente onde o sistema falha hoje sem dizer nada. Descobrir custa uma chamada a mais e elimina a classe inteira de erro.

*Alternativa considerada:* **`xrandr --listmonitors`** — descartada: lista apenas monitores **ativos**, então não veria a saída que se quer ligar. `--query` lista todas as saídas com o seu estado, que é o que interessa aqui e também na verificação de D3.

*A env var mantém a precedência máxima* para que o bring-up possa forçar um nome sem esperar por um novo build, como o `.xinitrc` já prevê nos comentários.

### D3. `activate()` verifica relendo o estado, e torna-se idempotente

Depois do `xrandr`, relê `--query` e confirma: alvo ativo, restantes inativas. Só então reporta sucesso.

O mesmo leitor serve de guarda de entrada: se o layout **já** corresponde ao pretendido, `activate()` não chama o `xrandr`. Isso resolve de graça a chamada redundante que D1 introduziria — `--apply-video-layout` no `.xinitrc` seguido do `point_x_at()` dentro do `run_mode` — que de outro modo causaria um flash de reconfiguração a cada arranque.

*Porquê:* o código de saída do `xrandr` diz que o comando foi aceite, não que o CRTC ficou como se pediu. No `modesetting` sobre `vc4-kms-v3d` o driver pode aceitar e não aplicar.

*Trade-off aceite:* mais duas execuções de `xrandr` por troca de tela. A troca é um evento raro (RF-09) e o timeout de 10 s já existente cobre o caso patológico.

### D4. O logging é configurado só no entrypoint, com ficheiro por omissão na imagem

`software/app.py` passa a chamar `logging.basicConfig` com um `FileHandler`. Caminho por omissão em `$HOME/calculadora.log` (o home do `kiosk`, criado pelo build e garantidamente gravável), sobreponível por `CALC_LOG_FILE`. Se o ficheiro não puder ser aberto, cai para stderr em vez de falhar o arranque.

*Porquê `$HOME` e não `/var/log`:* o rootfs é ext4 gravável (modo "sys"), mas o `kiosk` é utilizador comum e não tem escrita garantida em `/var/log`. `$HOME` remove essa dependência de permissões do caminho crítico de boot.

*Porquê só no entrypoint:* os módulos continuam com `getLogger(__name__)` e nenhum deles configura handlers — regra padrão de biblioteca, e o que mantém os testes silenciosos.

### D5. WRN-012 é reusado para a falha de layout, e permanece sem voz

A tabela do PRD §13 descreve WRN-012 como "HDMI / vídeo: mudança de estado ou **ausência temporária**", P2, com o anúncio marcado como opcional. Uma falha em pôr a UI no painel certo cabe aí.

*Porquê não um código novo:* a regra do projeto manda reusar antes de estender, e §13.3 exigiria registar o código novo no PRD — custo desproporcionado para um evento que ninguém além do bring-up vai ler.

*Porquê sem voz:* a fala do WRN-012 já está tomada pelo RF-09 (`video_watch.video_changed_speech`) e anuncia uma troca **bem-sucedida**. Anunciar também a falha usaria a mesma frase para dois sentidos opostos. A falha vai só para o log.

### D6. A janela dimensiona-se pela tela ativa, depois de o layout estar aplicado

`ui/hdmi/app.py` troca o `1280x720` fixo por `winfo_screenwidth()`/`winfo_screenheight()`, lidos na construção do `ttk.Window`.

*Porquê funciona:* `run_mode` já chama `point_x_at(next_mode)` **antes** de `start_front(next_mode, ...)`. Quando o Tk arranca, o framebuffer já é o do painel único, então a tela que o Tk vê é a certa. A ordem existente é o que torna isto uma alteração pequena em vez de uma coordenação nova.

*Mantém-se* `resizable(False, False)` e a grelha com pesos: sem gerenciador de janelas, uma janela do tamanho exato da tela é o equivalente ao ecrã cheio.

## Risks / Trade-offs

- **Parsing de `xrandr --query` é frágil a mudanças de formato** → só a primeira coluna de cada linha de saída e a palavra `connected`/`disconnected` são lidas; qualquer falha de parsing é tratada como "não verificável" (WRN-012 no log) e nunca como exceção. O front arranca de qualquer forma.
- **Duas chamadas extra de `xrandr` por troca** → mitigado pela guarda de idempotência de D3, que evita a reconfiguração quando o estado já está certo; e o custo só ocorre num evento raro.
- **Se o interruptor do LCD cortar só o backlight e não o HPD**, o LCD lê-se sempre `connected` e a exclusividade vai desligá-lo por `xrandr` quando o monitor chegar — que é o comportamento desejado. Mas com o interruptor desligado e sem monitor, o sistema continuaria a achar que há LCD utilizável. Essa limitação é anterior a esta mudança e já está registada no docstring de `SysfsHdmiPortReader`; permanece um item de bring-up.
- **Caminho legado/firmware (sem KMS)** → fora de escopo, como na proposta. O `--apply-video-layout` simplesmente não terá o que reconfigurar e regista WRN-012.
- **Risco de apagar a única tela** → `activate()` nunca desliga a saída alvo (já coberto por `test_the_target_is_never_switched_off_by_its_own_call`) e o modo `AUDIO_ONLY` não toca nas saídas. Os testes novos mantêm essas duas invariantes explícitas.
- **O log cresce sem rotação** → o ficheiro recebe poucas linhas por arranque; rotação fica de fora deliberadamente para não trazer dependência nem serviço novo. Se vier a incomodar, é uma mudança separada.

## Migration Plan

Não há dados nem estado persistido a migrar — o layout é sempre rederivado das portas.

1. Alterações de software entram primeiro e são cobertas por testes que correm sem X (CI verde antes de tocar na imagem).
2. `.xinitrc` e `README.md` da imagem entram a seguir, no mesmo PR.
3. Requer **rebuild da imagem** (`make rpi-img`) para chegar ao SD — o `.xinitrc` faz parte do overlay.
4. **Rollback:** reverter o commit e reconstruir. Sem passo de migração inverso.

## Open Questions

- Os nomes reais do `xrandr` neste kernel continuam por confirmar no hardware. A descoberta de D2 torna a resposta desnecessária para o código funcionar, mas o valor deve ser registado no `README.md` durante o bring-up, para que uma futura regressão seja reconhecível.
- Se o LCD, uma vez desligado por `xrandr`, volta a acender sozinho ao remover o monitor, ou se precisa de `--auto` explícito na saída de volta. O caminho de volta já passa pelo mesmo `activate()`, então a expectativa é que sim; confirma-se no item de bring-up que liga e desliga o monitor.
