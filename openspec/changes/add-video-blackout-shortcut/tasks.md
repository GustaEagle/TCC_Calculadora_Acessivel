## 1. Mecânica: desligar todas as saídas no X

- [x] 1.1 Em `software/hw_platform/video_output.py`, criar `all_off(outputs)` que monta **uma única** chamada `xrandr --output <A> --off --output <B> --off` com os nomes resolvidos por `output_name()` (design D3), e devolve `bool`. Verificar: teste unitário confirma o `argv` exato com os dois nomes.
- [x] 1.2 Após o `xrandr`, reler `read_outputs()` e só devolver `True` quando **nenhuma** saída estiver ativa; divergência ou estado ilegível → `False` e `logger.warning` com o código `WRN-013`. Verificar: teste com releitura *mockada* mostrando saída ainda ativa devolve `False`.
- [x] 1.3 Tratar o caso de só o LCD estar presente no X como sucesso, sem erro pela ausência do monitor (spec: «Apenas o LCD conectado»). Verificar: teste com `read_outputs()` devolvendo uma só saída.
- [x] 1.4 Garantir degradação sem X: sem `DISPLAY` ou sem binário `xrandr`, `all_off()` devolve `False` sem levantar exceção, reusando `available()`/`missing_xrandr_on_x()`. Verificar: teste com `DISPLAY` removido do ambiente.
- [x] 1.5 Acrescentar os testes de 1.1–1.4 a `software/tests/test_video_output.py`, seguindo o padrão de *mock* de `subprocess.run` já usado no ficheiro. Verificar: `python -m unittest software.tests.test_video_output -v` passa **sem** servidor X.

## 2. Estado de sessão e frases partilhadas

- [x] 2.1 Criar `software/ui/shared/video_blackout.py` com um objeto de sessão mutável (sinalizador `active`, inicial `False`) e **sem** importar Tk (design D1, D5). Verificar: `python -c "import software.ui.shared.video_blackout"` corre sem `DISPLAY`.
- [x] 2.2 No mesmo módulo, definir as frases do `WRN-013` — apagado (nomeando a tecla `AC` como via de retorno), religado (nomeando o painel), e falha ao apagar — como constantes/funções, no padrão de `video_changed_speech()` em `video_watch.py`. Verificar: teste confirma que a frase de desligamento contém a tecla e o prefixo «Aviso 013».
- [x] 2.3 Implementar a função de *toggle* que recebe o estado de sessão e um aplicador de vídeo injetável, inverte o sinalizador **só** quando o aplicador confirma sucesso, e devolve a frase a anunciar (spec: «Falha ao apagar é anunciada e não altera o estado»). Verificar: teste com aplicador que falha deixa `active == False` e devolve a frase de falha.
- [x] 2.4 Implementar a regra de recuperação por `AC`: com `active == True`, reacende e limpa o sinalizador; com `active == False`, não chama o aplicador (spec: «AC inalterado com a tela acesa»). Verificar: teste com duplo contando chamadas ao aplicador — zero com a tela acesa.
- [x] 2.5 Criar `software/tests/test_video_blackout.py` com os casos de 2.2–2.4. Verificar: passa sem `DISPLAY`.

## 3. Integração no laço de fronts

- [x] 3.1 Em `software/app.py`, construir o estado de sessão **uma vez** em `run_mode()`, ao lado do `CalculatorState`, e passá-lo a `point_x_at()` e a `start_front()` (design D1). Verificar: `software/tests/test_entrypoint_dispatch.py` continua a passar.
- [x] 3.2 Alterar `point_x_at()` para, com `active == True`, chamar `video_output.all_off()` em vez de `activate()`; com `False`, manter o comportamento atual intacto (design D2). Verificar: teste novo com `video_output` *mockado* confirma qual das duas funções é chamada em cada estado.
- [x] 3.3 Expor o reacendimento como chamada a `point_x_at(mode_atual)`, para que reacender reexecute a prioridade do §7.2 sem memorizar o painel anterior (spec: «Reacendimento respeita a prioridade de painel»). Verificar: teste em que o seletor simulado muda de LCD para HDMI entre apagar e religar confirma `activate()` com o monitor como alvo.
- [x] 3.4 Confirmar que a entrega do RF-09 preserva o blackout: com `active == True`, uma troca de front leva `point_x_at()` a chamar `all_off()` para o front seguinte (spec: «Hotplug durante o blackout não reacende a tela»). Verificar: teste do laço `run_mode()` com dois fronts simulados em sequência.
- [x] 3.5 Confirmar que `--force-mode audio` e o `AudioOnlyCalculator` **não** recebem nem usam o estado de blackout. Verificar: teste de *dispatch* do modo áudio inalterado.

## 4. Tecla e ligação nos dois fronts

- [x] 4.1 Em `software/ui/shared/keypad.py`, dar à tecla `AC` a função secundária `BLACKOUT` (`("AC", "AC", "BLACKOUT", None)`), retirar a tecla `?` inexistente na matriz (vira espaço vazio) e acrescentar o nome falado em `SPOKEN_TOKEN_NAMES` (design D4). Verificar: teste confirma que `BLACKOUT` só é alcançável como secundária de `AC`, que nenhuma tecla `?` resta no catálogo, e que `BLACKOUT` não coincide com nenhum token do §5.
- [x] 4.2 Em `software/hw_platform/keyboard.py`, **não** acrescentar atalho próprio: o PC usa `Ctrl` e depois `Esc`, como a matriz. Verificar: teste confirma que nenhuma tecla de `KEY_MAP` produz `BLACKOUT`.
- [x] 4.3 Em `software/ui/hdmi/app.py`, atribuir `BLACKOUT` como `secondary` quando `AC` chega do teclado sem ele (mesmo tratamento do `Ans`/`HISTORY`), tratar o token `BLACKOUT` depois da resolução dos modificadores, e tratar o caso `AC` sozinho chamando o módulo de 2.x e anunciando por `speech.interrupt_and_say()`. Verificar: teste de GUI (sob Xvfb) com `Ctrl` seguido de `AC` pela via do teclado confirma o anúncio e a inversão do estado com aplicador *mockado*.
- [x] 4.4 Espelhar 4.3 em `software/ui/lcd/app.py`, mantendo os dois `_handle_token()` equivalentes. Verificar: o mesmo teste parametrizado pelos dois fronts.
- [x] 4.5 Garantir que `Ctrl` + `AC` **não** limpa a expressão nem entra nela, **consome** o `Ctrl` como qualquer função secundária, e que o modo «o que faz esta tecla?» (`Ctrl`+`Shift`) apenas **descreve** `AC` com a sua função secundária, sem apagar a tela. Verificar: testes da expressão intacta e do `Ctrl` consumido nos dois fronts, e teste com `Ctrl`+`Shift` ativos no HDMI confirmando descrição falada e estado de vídeo inalterado.
- [x] 4.6 Verificar o requisito «Calculadora permanece operável»: com `active == True`, digitar `2+2`, `=`, confirmar resultado anunciado e presença no histórico; religar e confirmar expressão, `Ans`, histórico e modo graus/radianos intactos. Verificar: teste de GUI de ponta a ponta com aplicador *mockado*.

## 5. Dimensionamento durante o blackout

- [x] 5.1 No front HDMI, quando o front é construído com `active == True`, dimensionar pela geometria preferida da saída-alvo em vez de `video_output.screen_size()`, caindo para o comportamento atual quando ilegível (design D7). Verificar: teste com `screen_size()` *mockado* a devolver tamanho degenerado confirma que a faixa de layout escolhida corresponde à saída-alvo.
- [x] 5.2 Confirmar que, com `active == False`, o dimensionamento é **exatamente** o atual. Verificar: `software/tests/test_window_geometry.py` e `test_hdmi_layout_wiring.py` passam sem alterações.

## 6. Documentação e registo do código

- [x] 6.1 Registar `WRN-013` na tabela do `docs/produto/PRD.md` §13 (P2, «Telas desligadas/religadas por comando»), com a frase falada, e acrescentar entrada no histórico de versões do PRD. Verificar: a linha existe entre `WRN-012` e `WRN-020`.
- [x] 6.2 Em `docs/guias/comandos-teclado.md`, retirar `?` da lista de teclas reservadas (§3; ela não existe na matriz), acrescentar `Ctrl` + `AC` às tabelas do teclado físico e `Ctrl` e depois `Esc` à do PC (com a nota do menu Iniciar no Windows), e documentar a recuperação por `AC`. Verificar: nenhuma menção residual a `?` como tecla nem a `v` como atalho.
- [x] 6.3 Em `system/rpi-os/alpine/README.md`, acrescentar à checklist de bring-up os itens da secção 7. Verificar: itens presentes na checklist.

## 7. Verificação no hardware (Raspberry Pi 4B)

- [ ] 7.1 Com só o LCD ligado, pressionar `Ctrl` e depois `AC`: o LCD apaga e o anúncio `WRN-013` é ouvido. Verificar: `xrandr --query` mostra a saída do LCD sem geometria ativa, e `~/calculadora.log` regista o sucesso.
- [ ] 7.2 **Hipótese crítica (design, Riscos):** com as telas apagadas, digitar `2+2=` e confirmar o resultado falado — prova de que as teclas continuam a chegar à janela Tk sem CRTC ativo. Se falhar, **parar** e reabrir o design antes de continuar.
- [ ] 7.3 Confirmar se o driver `modesetting` aceita desligar o último CRTC. Se recusar, confirmar que o anúncio é o de falha, que a tela permanece acesa, e registar o resultado no `README.md` da imagem.
- [ ] 7.4 Com LCD e monitor ligados, pressionar `Ctrl` + `AC`: as duas saídas apagam. Pressionar `Ctrl` + `AC` de novo: reacende **só** o monitor. Verificar por `xrandr --query`.
- [ ] 7.5 Com as telas apagadas, ligar o monitor externo, aguardar a entrega de front, e confirmar que **nenhum** painel acende; depois pressionar `AC` e confirmar que o monitor reacende com a expressão limpa.
- [ ] 7.6 Encerrar a calculadora com as telas apagadas e reiniciá-la: arranca acesa. Verificar visualmente.
- [ ] 7.7 Medir e registar se o LCD Waveshare corta a retroiluminação sem sinal ou mostra «sem sinal» iluminado (alimenta a Open Question de autonomia). Verificar: resultado registado no `README.md` da imagem.

## 8. Fecho

- [x] 8.1 Correr a suíte completa como o CI: `xvfb-run -a python -m unittest discover -s software/tests -t . -v`. Verificar: todos os testes passam, incluindo os pré-existentes.
- [x] 8.2 Validar a mudança: `openspec validate add-video-blackout-shortcut --strict`. Verificar: sem erros.
