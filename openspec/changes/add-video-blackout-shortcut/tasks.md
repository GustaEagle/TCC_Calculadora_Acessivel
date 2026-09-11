## 1. Mecânica: desligar todas as saídas no X

- [ ] 1.1 Em `software/hw_platform/video_output.py`, criar `all_off(outputs)` que monta **uma única** chamada `xrandr --output <A> --off --output <B> --off` com os nomes resolvidos por `output_name()` (design D3), e devolve `bool`. Verificar: teste unitário confirma o `argv` exato com os dois nomes.
- [ ] 1.2 Após o `xrandr`, reler `read_outputs()` e só devolver `True` quando **nenhuma** saída estiver ativa; divergência ou estado ilegível → `False` e `logger.warning` com o código `WRN-013`. Verificar: teste com releitura *mockada* mostrando saída ainda ativa devolve `False`.
- [ ] 1.3 Tratar o caso de só o LCD estar presente no X como sucesso, sem erro pela ausência do monitor (spec: «Apenas o LCD conectado»). Verificar: teste com `read_outputs()` devolvendo uma só saída.
- [ ] 1.4 Garantir degradação sem X: sem `DISPLAY` ou sem binário `xrandr`, `all_off()` devolve `False` sem levantar exceção, reusando `available()`/`missing_xrandr_on_x()`. Verificar: teste com `DISPLAY` removido do ambiente.
- [ ] 1.5 Acrescentar os testes de 1.1–1.4 a `software/tests/test_video_output.py`, seguindo o padrão de *mock* de `subprocess.run` já usado no ficheiro. Verificar: `python -m unittest software.tests.test_video_output -v` passa **sem** servidor X.

## 2. Estado de sessão e frases partilhadas

- [ ] 2.1 Criar `software/ui/shared/video_blackout.py` com um objeto de sessão mutável (sinalizador `active`, inicial `False`) e **sem** importar Tk (design D1, D5). Verificar: `python -c "import software.ui.shared.video_blackout"` corre sem `DISPLAY`.
- [ ] 2.2 No mesmo módulo, definir as frases do `WRN-013` — apagado (nomeando a tecla `?` como via de retorno), religado (nomeando o painel), e falha ao apagar — como constantes/funções, no padrão de `video_changed_speech()` em `video_watch.py`. Verificar: teste confirma que a frase de desligamento contém a tecla e o prefixo «Aviso 013».
- [ ] 2.3 Implementar a função de *toggle* que recebe o estado de sessão e um aplicador de vídeo injetável, inverte o sinalizador **só** quando o aplicador confirma sucesso, e devolve a frase a anunciar (spec: «Falha ao apagar é anunciada e não altera o estado»). Verificar: teste com aplicador que falha deixa `active == False` e devolve a frase de falha.
- [ ] 2.4 Implementar a regra de recuperação por `AC`: com `active == True`, reacende e limpa o sinalizador; com `active == False`, não chama o aplicador (spec: «AC inalterado com a tela acesa»). Verificar: teste com duplo contando chamadas ao aplicador — zero com a tela acesa.
- [ ] 2.5 Criar `software/tests/test_video_blackout.py` com os casos de 2.2–2.4. Verificar: passa sem `DISPLAY`.

## 3. Integração no laço de fronts

- [ ] 3.1 Em `software/app.py`, construir o estado de sessão **uma vez** em `run_mode()`, ao lado do `CalculatorState`, e passá-lo a `point_x_at()` e a `start_front()` (design D1). Verificar: `software/tests/test_entrypoint_dispatch.py` continua a passar.
- [ ] 3.2 Alterar `point_x_at()` para, com `active == True`, chamar `video_output.all_off()` em vez de `activate()`; com `False`, manter o comportamento atual intacto (design D2). Verificar: teste novo com `video_output` *mockado* confirma qual das duas funções é chamada em cada estado.
- [ ] 3.3 Expor o reacendimento como chamada a `point_x_at(mode_atual)`, para que reacender reexecute a prioridade do §7.2 sem memorizar o painel anterior (spec: «Reacendimento respeita a prioridade de painel»). Verificar: teste em que o seletor simulado muda de LCD para HDMI entre apagar e religar confirma `activate()` com o monitor como alvo.
- [ ] 3.4 Confirmar que a entrega do RF-09 preserva o blackout: com `active == True`, uma troca de front leva `point_x_at()` a chamar `all_off()` para o front seguinte (spec: «Hotplug durante o blackout não reacende a tela»). Verificar: teste do laço `run_mode()` com dois fronts simulados em sequência.
- [ ] 3.5 Confirmar que `--force-mode audio` e o `AudioOnlyCalculator` **não** recebem nem usam o estado de blackout. Verificar: teste de *dispatch* do modo áudio inalterado.

## 4. Tecla e ligação nos dois fronts

- [ ] 4.1 Em `software/ui/shared/keypad.py`, dar à tecla `?` o token primário `BLACKOUT` e acrescentar o nome falado em `SPOKEN_TOKEN_NAMES` (design D4). Verificar: teste confirma que `BLACKOUT` não coincide com nenhum token do catálogo do §5 (spec: «Tecla escolhida não colide com o catálogo matemático»).
- [ ] 4.2 Em `software/hw_platform/keyboard.py`, mapear `v`/`V` → `BLACKOUT` em `KEY_MAP`, com comentário explicando por que não `?` (exige `Shift`, que acende o indicador). Verificar: teste de `map_key("v") == "BLACKOUT"`.
- [ ] 4.3 Em `software/ui/hdmi/app.py`, ligar `<question>` em `_bind_keyboard()` e tratar `BLACKOUT` e o caso `AC` em `_handle_token()` chamando o módulo de 2.x e anunciando por `speech.interrupt_and_say()`. Verificar: teste de GUI (sob Xvfb) pressionando `v` confirma o anúncio e a inversão do estado com aplicador *mockado*.
- [ ] 4.4 Espelhar 4.3 em `software/ui/lcd/app.py`, mantendo os dois `_handle_token()` equivalentes. Verificar: o mesmo teste parametrizado pelos dois fronts.
- [ ] 4.5 Garantir que `BLACKOUT` **não** é inserido na expressão, **não** consome `Ctrl`/`Shift` ativos e **não** dispara o modo «o que faz esta tecla?» de `Ctrl`+`Shift` de forma a apagar a tela. Verificar: teste com `Ctrl`+`Shift` ativos confirma descrição falada e estado de vídeo inalterado.
- [ ] 4.6 Verificar o requisito «Calculadora permanece operável»: com `active == True`, digitar `2+2`, `=`, confirmar resultado anunciado e presença no histórico; religar e confirmar expressão, `Ans`, histórico e modo graus/radianos intactos. Verificar: teste de GUI de ponta a ponta com aplicador *mockado*.

## 5. Dimensionamento durante o blackout

- [ ] 5.1 No front HDMI, quando o front é construído com `active == True`, dimensionar pela geometria preferida da saída-alvo em vez de `video_output.screen_size()`, caindo para o comportamento atual quando ilegível (design D7). Verificar: teste com `screen_size()` *mockado* a devolver tamanho degenerado confirma que a faixa de layout escolhida corresponde à saída-alvo.
- [ ] 5.2 Confirmar que, com `active == False`, o dimensionamento é **exatamente** o atual. Verificar: `software/tests/test_window_geometry.py` e `test_hdmi_layout_wiring.py` passam sem alterações.

## 6. Documentação e registo do código

- [ ] 6.1 Registar `WRN-013` na tabela do `PRD.md` §13 (P2, «Telas desligadas/religadas por comando»), com a frase falada, e acrescentar entrada no histórico de versões do PRD. Verificar: a linha existe entre `WRN-012` e `WRN-020`.
- [ ] 6.2 Em `docs/comandos-teclado.md`, retirar `?` da lista de teclas reservadas (§3), acrescentar o comando às tabelas do teclado físico e do PC (`v`, `?`), e documentar a recuperação por `AC`. Verificar: nenhuma menção residual a «`?` reservada».
- [ ] 6.3 Em `system/rpi-os/alpine/README.md`, acrescentar à checklist de bring-up os itens da secção 7. Verificar: itens presentes na checklist.

## 7. Verificação no hardware (Raspberry Pi 4B)

- [ ] 7.1 Com só o LCD ligado, pressionar `?`: o LCD apaga e o anúncio `WRN-013` é ouvido. Verificar: `xrandr --query` mostra a saída do LCD sem geometria ativa, e `~/calculadora.log` regista o sucesso.
- [ ] 7.2 **Hipótese crítica (design, Riscos):** com as telas apagadas, digitar `2+2=` e confirmar o resultado falado — prova de que as teclas continuam a chegar à janela Tk sem CRTC ativo. Se falhar, **parar** e reabrir o design antes de continuar.
- [ ] 7.3 Confirmar se o driver `modesetting` aceita desligar o último CRTC. Se recusar, confirmar que o anúncio é o de falha, que a tela permanece acesa, e registar o resultado no `README.md` da imagem.
- [ ] 7.4 Com LCD e monitor ligados, pressionar `?`: as duas saídas apagam. Pressionar `?` de novo: reacende **só** o monitor. Verificar por `xrandr --query`.
- [ ] 7.5 Com as telas apagadas, ligar o monitor externo, aguardar a entrega de front, e confirmar que **nenhum** painel acende; depois pressionar `AC` e confirmar que o monitor reacende com a expressão limpa.
- [ ] 7.6 Encerrar a calculadora com as telas apagadas e reiniciá-la: arranca acesa. Verificar visualmente.
- [ ] 7.7 Medir e registar se o LCD Waveshare corta a retroiluminação sem sinal ou mostra «sem sinal» iluminado (alimenta a Open Question de autonomia). Verificar: resultado registado no `README.md` da imagem.

## 8. Fecho

- [ ] 8.1 Correr a suíte completa como o CI: `xvfb-run -a python -m unittest discover -s software/tests -t . -v`. Verificar: todos os testes passam, incluindo os pré-existentes.
- [ ] 8.2 Validar a mudança: `openspec validate add-video-blackout-shortcut --strict`. Verificar: sem erros.
