## Why

Com o LCD e o monitor externo ligados ao mesmo tempo, o produto está mostrando um **desktop estendido** nas duas telas em vez de usar só o monitor. Isso viola o PRD §7.2 ("a interface é exibida **apenas** no monitor externo... o LCD **não** deve apresentar a mesma interface principal") e os requisitos RF-02 e RF-03.

A regra de prioridade em si já está correta em `software/hw_platform/display.py` (`DisplaySelector.current_mode()` devolve `HDMI` quando os dois estão presentes, e há testes cobrindo isso). O que falha é a etapa seguinte — **fazer o X obedecer a essa decisão**. Três lacunas, todas fora do `core/`:

1. **O boot nunca define um layout exclusivo.** O overlay da imagem Alpine (`system/rpi-os/alpine/overlay/`) não traz nenhum `xorg.conf`/`xorg.conf.d`, e o `.xinitrc` não chama `xrandr` antes de subir o app. Com as duas portas conectadas, o driver `modesetting` autoconfigura os dois CRTCs lado a lado. O desktop estendido já existe **antes** de o Python arrancar.
2. **A correção do app falha em silêncio.** `video_output.activate()` monta um único `xrandr` com `check=True` usando nomes **adivinhados** por `drm_to_xrandr()` (`HDMI-A-1` → `HDMI-1`). Se este kernel/driver usar outra convenção, o comando sai com erro, `activate()` devolve `False`, e o layout estendido permanece — exatamente o sintoma observado. As variáveis `CALC_LCD_XRANDR_OUTPUT` / `CALC_MONITOR_XRANDR_OUTPUT` existem para corrigir isso, mas continuam **comentadas** no `.xinitrc`, e o item "conferir os nomes do `xrandr --listmonitors`" segue por marcar na checklist de bring-up do `system/rpi-os/alpine/README.md`.
3. **Não há como diagnosticar.** Não existe `logging.basicConfig` em lugar nenhum de `software/`; o `logger.warning("xrandr falhou...")` sai no tty1, que está coberto pelo X. Ninguém vê nem o sucesso nem a falha.

Some-se a isso que a janela é `1280x720` fixa e `resizable(False, False)`, sem gerenciador de janelas: num framebuffer combinado o X a coloca em (0,0), ou seja, no canto do **LCD**, não no monitor.

## What Changes

- **Layout exclusivo já no arranque da sessão gráfica.** Novo subcomando `python3 -m software.app --apply-video-layout`, que consulta o `DisplaySelector` e aplica o layout exclusivo via `xrandr`, sem abrir UI. O `.xinitrc` passa a chamá-lo **antes** do laço do app, para que o desktop estendido nunca chegue a ser visível. A regra de prioridade continua a viver só em `display.py` — o shell não a duplica.
- **Descobrir os nomes do `xrandr` em vez de adivinhar.** `video_output` passa a ler as saídas reais de `xrandr --query` e a casar cada conector DRM com a saída X correspondente; a convenção `drm_to_xrandr()` e as variáveis de ambiente ficam como fallback e override, nesta ordem: env var → saída realmente presente no X → convenção. Elimina a falha silenciosa por nome errado.
- **Verificar o resultado em vez de confiar no código de saída.** Depois do `xrandr`, `activate()` relê o estado das saídas e confirma que só a alvo está ativa. Divergência é registrada como **WRN-012** (PRD §13 — "HDMI / vídeo: mudança de estado ou ausência temporária"), sem inventar código novo e sem anúncio por voz (P2, e a tabela deixa o anúncio como opcional).
- **Log em ficheiro na imagem.** Configuração mínima de `logging` no entrypoint, escrevendo para um ficheiro no rootfs, para que o bring-up consiga ver o que o `xrandr` fez sem desmontar o kiosk.
- **`--list-outputs` cobre os dois lados.** Passa a imprimir também as saídas vistas pelo `xrandr` e o mapeamento DRM → X efetivamente em uso, fechando num só comando os itens da checklist de bring-up que hoje pedem dois.
- **Janela ocupa o painel ativo.** O front do monitor dimensiona-se pela geometria da saída ativa em vez do `1280x720` fixo, para não ficar num canto do framebuffer.
- **Documentação.** `system/rpi-os/alpine/README.md` ganha a secção do caso "dois HDMI ligados" e a checklist passa a verificar explicitamente que o LCD apaga.

## Capabilities

### New Capabilities
- `video-output-exclusivity`: garantir que, em qualquer combinação de portas HDMI reconhecidas, **exatamente uma** saída de vídeo está ativa no servidor X — incluindo o estado inicial da sessão gráfica, a verificação de que o comando surtiu efeito, e o diagnóstico quando não surtiu.

### Modified Capabilities
(nenhuma — `openspec/specs/` está vazio; `display-switching` ainda vive na mudança `add-hdmi-ui`, não sincronizada. A prioridade monitor > LCD lá especificada permanece **inalterada**: esta mudança faz cumpri-la, não a redefine.)

## Impact

- **Código alterado:** `software/hw_platform/video_output.py` (descoberta de nomes + verificação pós-aplicação), `software/app.py` (subcomando `--apply-video-layout`, `--list-outputs` estendido, configuração de logging), `software/ui/hdmi/app.py` (dimensionamento pela saída ativa).
- **Sistema/imagem alterada:** `system/rpi-os/alpine/overlay/home/kiosk/.xinitrc` (chamada do layout antes do laço), `system/rpi-os/alpine/README.md` (bring-up).
- **Sem alteração:** `software/core/` (o motor continua agnóstico de UI), `software/hw_platform/display.py` (a regra do §7 já está certa), catálogo de erros do PRD §13 (WRN-012 é reusado), `usercfg.txt` (`max_framebuffers=2` **tem de ficar** — é o que dá hotplug da 2ª porta para o RF-09; a exclusividade resolve-se no X, não castrando o firmware).
- **Testes novos** em `software/tests/` para a descoberta de nomes, a verificação pós-`xrandr` e o subcomando de layout. Os testes continuam a correr sem X (o caminho `xrandr` é mockado, como em `test_video_output.py`).
- **Requisitos cobertos:** RF-02, RF-03, RF-09; PRD §7.2 e §7.4.

## Não-objetivos

- **Não** alterar o escopo matemático do PRD §5 nem o catálogo de erros do §13 (WRN-012 é reusado, nenhum código novo é criado).
- **Não** acoplar `core/` a nenhuma stack de UI nem ao `xrandr`.
- **Não** introduzir gerenciador de janelas nem compositor na imagem do kiosk.
- **Não** suportar espelhamento (mirror) nem uso simultâneo das duas telas: o PRD §7.2 é explícito em que só uma mostra a UI.
- **Não** resolver o caso do caminho legado/firmware (sem KMS), em que o modo é fixado no boot e o hotplug não existe — continua registrado como limitação no `README.md` da imagem.
- **Não** unificar os fronts `ui/lcd` e `ui/hdmi`.
