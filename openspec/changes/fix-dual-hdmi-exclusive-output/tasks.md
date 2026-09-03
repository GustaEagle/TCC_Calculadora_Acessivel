## 1. Descoberta dos nomes de saída do xrandr (D2)

- [ ] 1.1 Em `software/hw_platform/video_output.py`, adicionar uma leitura das saídas conhecidas pelo servidor X via `xrandr --query`, devolvendo nome e estado ativo/inativo de cada uma; verificar com teste novo em `software/tests/test_video_output.py` que mocka `subprocess.run` com uma amostra real de `--query` e confere o dicionário resultante.
- [ ] 1.2 Tratar `xrandr` ausente, com timeout, com erro, ou com saída em formato inesperado como "nenhuma saída conhecida" em vez de exceção; verificar com testes que cada um dos quatro casos devolve vazio e não levanta.
- [ ] 1.3 Reescrever `output_name()` para a precedência de D2 (env var → saída presente no X que casa com o conector → convenção `drm_to_xrandr()`), com normalização que trate `HDMI-A-2`, `HDMI-2`, `HDMI2` e `hdmi-2` como a mesma porta; verificar com testes cobrindo os três níveis de precedência e o casamento sem hífen.
- [ ] 1.4 Confirmar que os testes existentes de `drm_to_xrandr()` e do override por env var continuam a passar sem alteração, garantindo que a máquina de desenvolvimento (sem `DISPLAY`) recai na convenção; verificar rodando `python -m unittest software.tests.test_video_output -v`.

## 2. Verificação e idempotência do layout (D3)

- [ ] 2.1 Adicionar em `video_output` uma função que compara o estado lido em 1.1 com o layout pretendido (alvo ativo, restantes inativas) e devolve se já corresponde; verificar com testes para os casos "já correto", "estendido", "painel errado ativo" e "estado não legível".
- [ ] 2.2 Fazer `activate()` sair como sucesso sem chamar `xrandr` quando o layout já corresponde ao pretendido; verificar com teste que `subprocess.run` não é chamado nesse caso.
- [ ] 2.3 Fazer `activate()` reler o estado após o `xrandr` e só reportar sucesso se a verificação passar; verificar com teste em que o `xrandr` devolve código 0 mas a releitura mostra o LCD ainda ativo, e `activate()` devolve `False`.
- [ ] 2.4 Garantir que as invariantes de segurança se mantêm: a saída alvo nunca é desligada pela própria chamada, e um estado não verificável não impede o arranque; verificar mantendo verde `test_the_target_is_never_switched_off_by_its_own_call` e adicionando um teste para o estado não verificável.

## 3. Logging diagnosticável (D4)

- [ ] 3.1 Configurar `logging` em `software/app.py` com `FileHandler` em `$HOME/calculadora.log`, sobreponível por `CALC_LOG_FILE`, com fallback para stderr quando o ficheiro não abre; verificar com teste que aponta `CALC_LOG_FILE` para um ficheiro temporário e confirma que uma mensagem lá aparece, e com um segundo teste para o caminho inválido que não levanta.
- [ ] 3.2 Registar em `activate()` o resultado da aplicação do layout — modo pretendido, nomes de saída usados, e sucesso ou falha —, usando o prefixo WRN-012 nas falhas conforme D5; verificar com teste que captura os registros (`assertLogs`) numa falha simulada e confirma a presença de "WRN-012", do modo e dos nomes.
- [ ] 3.3 Confirmar que nenhum módulo fora do entrypoint configura handlers de logging; verificar com `grep -rn "basicConfig\|addHandler" software/` retornando ocorrência apenas em `software/app.py`.

## 4. Aplicação do layout sem UI (D1)

- [ ] 4.1 Adicionar a flag `--apply-video-layout` a `build_parser()` em `software/app.py`, que resolve o modo pelo `DisplaySelector`, chama `point_x_at()` e encerra sem instanciar front; verificar com teste que mocka `video_output.activate` e confirma que nem `ui/lcd` nem `ui/hdmi` são importados.
- [ ] 4.2 Fazer o modo `AUDIO_ONLY` não emitir nenhuma reconfiguração nesse caminho; verificar com teste que `activate` não é chamado quando o selector devolve `AUDIO_ONLY`.
- [ ] 4.3 Garantir que a flag é compatível com `--force-mode` (útil para demonstrar o layout sem o hardware) e mutuamente coerente com `--list-outputs`; verificar com testes em `software/tests/test_entrypoint_dispatch.py` para as combinações.

## 5. Diagnóstico de bring-up (spec: Diagnóstico de bring-up cobre DRM e X)

- [ ] 5.1 Estender `print_outputs()` para imprimir também as saídas conhecidas pelo `xrandr` com o seu estado, e para cada papel (LCD, monitor) o par conector DRM / saída X efetivamente resolvido; verificar com teste que mocka as duas leituras e confere as três secções na saída.
- [ ] 5.2 Fazer o comando reportar de forma explícita a ausência de conectores DRM e a ausência de servidor X, encerrando com código 0; verificar com teste numa máquina simulada sem nenhum dos dois.

## 6. Sessão gráfica da imagem (D1)

- [ ] 6.1 Em `system/rpi-os/alpine/overlay/home/kiosk/.xinitrc`, invocar `python3 -m software.app --apply-video-layout` a partir de `/opt/calculadora`, depois dos `xset` e antes do laço `while true`, com comentário explicando que serve para o desktop estendido autoconfigurado nunca ficar visível; verificar por inspeção do ficheiro e com `sh -n` sobre ele.
- [ ] 6.2 Fazer o laço de reinício não repetir a aplicação do layout a cada volta (o `run_mode` já o faz por dentro), mantendo a chamada única antes do laço; verificar por inspeção de que a linha está fora do `while`.
- [ ] 6.3 Confirmar que `usercfg.txt` permanece inalterado, em particular `dtoverlay=vc4-kms-v3d` e `max_framebuffers=2`; verificar com `git diff --stat` mostrando o ficheiro fora do conjunto de alterações.

## 7. Geometria da janela (D6)

- [ ] 7.1 Em `software/ui/hdmi/app.py`, substituir o `geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")` fixo por dimensionamento a partir de `winfo_screenwidth()`/`winfo_screenheight()`, mantendo `resizable(False, False)`; verificar com teste que instancia o front com uma tela simulada de 1920x1080 e confere a geometria pedida.
- [ ] 7.2 Confirmar que a grelha continua a distribuir o espaço extra sem sobreposição nem truncamento inesperado em resolução maior; verificar mantendo verdes `test_expression_display.py`, `test_contrast.py` e `test_keypad_toggle.py`.

## 8. Documentação e verificação de sistema

- [ ] 8.1 Acrescentar ao `system/rpi-os/alpine/README.md` a secção do caso "dois HDMI ligados ao mesmo tempo", explicando por que o X estende por omissão e como o `--apply-video-layout` o corrige; verificar por revisão do texto contra o PRD §7.2.
- [ ] 8.2 Acrescentar à checklist de bring-up os itens: (a) com as duas portas ligadas no boot, **só o monitor** acende e o LCD fica apagado; (b) registar no README os nomes reais devolvidos por `xrandr --query`; (c) confirmar no `calculadora.log` que o layout foi aplicado e verificado; verificar por revisão da checklist.
- [ ] 8.3 Rodar a suíte completa e confirmar que continua verde sem `DISPLAY` e sem HDMI, como no CI; verificar com `python -m unittest discover -s software/tests -t . -v`.

## 9. Validação no hardware (fecha as Open Questions do design)

- [ ] 9.1 Reconstruir a imagem (`make rpi-img`) e gravar no SD; verificar que o Pi arranca na calculadora.
- [ ] 9.2 Arrancar com LCD e monitor ambos ligados; verificar que a UI aparece **apenas** no monitor, que o LCD não mostra área de trabalho nenhuma, e que nunca há um instante de desktop estendido visível.
- [ ] 9.3 Com a calculadora já a correr no LCD, ligar o monitor externo; verificar que a UI passa para o monitor, o LCD apaga, e a expressão em curso e o histórico sobrevivem (RF-09).
- [ ] 9.4 Remover o monitor; verificar que o LCD volta a acender sozinho com a UI e o estado preservado, respondendo à segunda Open Question do design.
- [ ] 9.5 Registar no `system/rpi-os/alpine/README.md` os nomes de saída reais observados, fechando a primeira Open Question do design.
