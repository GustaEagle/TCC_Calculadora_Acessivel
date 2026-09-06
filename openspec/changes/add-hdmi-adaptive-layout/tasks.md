## 1. Regra de layout como módulo puro

- [ ] 1.1 Criar `software/ui/shared/layout.py` com as constantes nomeadas: `REFERENCE_WIDTH/HEIGHT` (1280x720), `KEYPAD_MIN_WIDTH/HEIGHT` (900x600), `HISTORY_MIN_WIDTH/HEIGHT` (1200x700), `SCALE_FLOOR` (0.75) e `SCALE_CEILING` (2.0), com comentário explicando a origem de cada limiar (design D3).
- [ ] 1.2 Definir `LayoutTier` (`COMPACT` / `MEDIUM` / `FULL`) e `tier_for(width, height)`, exigindo que **ambas** as dimensões atinjam o limiar (design D3).
- [ ] 1.3 Implementar `scale_for(width, height)` = `clamp(min(w/REF_W, h/REF_H), SCALE_FLOOR, SCALE_CEILING)` (design D4).
- [ ] 1.4 Implementar `font_sizes(scale)` a partir da tabela base atual e `display_limits(scale)`, que ajusta `MAX_EXPRESSION_CHARS`/`MAX_RESULT_CHARS` **inversamente** à escala.
- [ ] 1.5 Garantir que o módulo **não importa Tk/ttkbootstrap** (é o que o torna testável sem display).

## 2. Testes da regra (sem abrir janela)

- [ ] 2.1 Criar `software/tests/test_hdmi_layout_tiers.py` cobrindo as três faixas, incluindo os **limites exatos** (ex.: 900x600 é média; 899x600 e 900x599 são compacta).
- [ ] 2.2 Testar que uma tela larga e baixa (ex.: 1920x480) **não** ganha teclado — a regra é por eixo, não por área.
- [ ] 2.3 Testar piso e teto da escala (ex.: 640x480 → `SCALE_FLOOR`; 3840x2160 → `SCALE_CEILING`).
- [ ] 2.4 **Teste de não-regressão:** em 1280x720 a escala é 1.0 e `font_sizes(1.0)` reproduz exatamente os valores de `FONT_SIZES` de hoje (34/58/17/13/14).
- [ ] 2.5 Testar que `display_limits` reduz o número de caracteres quando a escala cresce.
- [ ] 2.6 Confirmar que os novos testes passam **sem** `DISPLAY` (`env -u DISPLAY python3 -m unittest ...`).

## 3. Consumir a regra no front HDMI

- [ ] 3.1 Em [software/ui/hdmi/app.py](../../../software/ui/hdmi/app.py), derivar `self.tier` e `self.scale` na construção, a partir de `winfo_screenwidth/height` (mesma fonte já usada por `_screen_geometry`).
- [ ] 3.2 Substituir o `FONT_SIZES` fixo e as constantes `MAX_*_CHARS` pelos valores derivados da escala, mantendo `resizable(False, False)`.
- [ ] 3.3 Em `_build_layout`, montar o painel de histórico **apenas** na faixa completa — sem criar o widget nas demais, e sem deixar peso de coluna reservado (design D5).
- [ ] 3.4 Montar o teclado (`keypad_frame`, `left_frame`, `right_frame`, botões) **apenas** nas faixas média e completa.
- [ ] 3.5 Omitir o botão de alternar teclado no rodapé quando não há teclado, e ajustar `_set_initial_focus` para um alvo que exista em qualquer faixa.
- [ ] 3.6 Tornar `_apply_controls_visibility` e `_update_keypad_labels` tolerantes a `self.buttons` vazio e a `keypad_frame` inexistente (faixa compacta).
- [ ] 3.7 Conferir que a construção do front na troca de saída (RF-09) relê a tela nova — nada de estado de layout em variável de módulo.

## 4. Testes do front (com display)

- [ ] 4.1 Acrescentar a `software/tests/` um teste que constrói o front e verifica que, na faixa completa, existem teclado, histórico e botão de alternância — usando o padrão dos testes de GUI já existentes (rodam sob Xvfb no CI).
- [ ] 4.2 Verificar que a suíte completa continua passando (`make check`) e que o total de testes headless não regride.

## 5. Validação no hardware (Raspberry Pi 4B + monitor)

- [ ] 5.1 No monitor do TCC, confirmar a faixa **completa**: display, teclado e histórico legíveis, sem sobreposição nem corte.
- [ ] 5.2 Confirmar que a escala tipográfica melhora a leitura em relação ao layout fixo anterior (público com visão parcial, PRD §4).
- [ ] 5.3 Se houver monitor menor disponível, confirmar as faixas **média** e **compacta**; senão, registrar que ficaram cobertas apenas por teste unitário.
- [ ] 5.4 Confirmar que, na faixa compacta, a calculadora continua **totalmente operável pelo teclado físico** (RF-05) e que os anúncios de voz não mudam.
- [ ] 5.5 Revisar os limiares (D3) com o que foi observado e ajustar as constantes se o histórico ou o teclado ficarem apertados.

## 6. Documentação

- [ ] 6.1 Atualizar o docstring de [software/ui/hdmi/app.py](../../../software/ui/hdmi/app.py): ele hoje afirma que as fontes são declaradas uma vez e fixas — passa a ser "derivadas da resolução na construção, sem recomposição em runtime".
- [ ] 6.2 Registrar as três faixas e os limiares onde a equipe encontre (README do software ou `docs/`), para que ajustar um número não exija ler o front inteiro.
