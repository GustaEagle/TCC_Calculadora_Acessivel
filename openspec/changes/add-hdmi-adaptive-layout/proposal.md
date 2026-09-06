## Why

O front do monitor externo assume hoje uma composição única: janela do tamanho da tela, mas **fontes fixas** (calibradas para ~1280x720) e **histórico sempre visível**. Num monitor 4K o texto fica pequeno demais para o público-alvo (visão parcial, PRD §4); num monitor pequeno (ex.: 1024x768) o teclado de 7 colunas e o painel de histórico espremem a expressão e o resultado — justamente o que precisa continuar legível.

O requisito `hdmi-ui` "Layout responsivo à resolução do monitor" já existe, mas está **parcialmente cumprido**: a realocação por `grid`/`weight` funciona, a **escala tipográfica não**. Este change fecha essa lacuna e adiciona o comportamento que falta — **omitir teclado e histórico quando não cabem**, no espírito da calculadora do Windows.

## What Changes

- **Escala proporcional:** fontes, paddings e limites de truncamento do display passam a derivar da resolução real da tela, em vez de constantes fixas. Um fator de escala com piso e teto evita tanto texto ilegível quanto letras gigantes.
- **Faixas de tamanho (tiers):** o front escolhe, **no arranque**, uma entre três composições conforme a resolução:
  - **compacta** — apenas expressão + resultado (sem teclado, sem histórico);
  - **média** — expressão + resultado + teclado (sem histórico);
  - **completa** — comportamento atual (expressão + resultado + teclado + histórico).
- **Teclado e histórico condicionais:** abaixo do limiar, o painel simplesmente **não é montado** — e o botão de alternar teclado some junto, para não oferecer uma ação impossível a quem navega por Tab/voz.
- **Sem caminho de resize:** a decisão continua sendo tomada **uma única vez**, na construção; a janela permanece `resizable(False, False)`. Isso preserva a propriedade que o front já tinha (não há re-layout em runtime para dar errado) e casa com o kiosk do Pi, onde a janela é sempre do tamanho do painel.
- **BREAKING (spec, não código):** o cenário "Redimensionamento manual da janela" do requisito existente deixa de valer como escrito — a janela nunca foi redimensionável, então o cenário descrevia um comportamento que o código não tem.

## Capabilities

### New Capabilities

<!-- Nenhuma: o comportamento pertence à capability hdmi-ui, que já existe. -->

### Modified Capabilities

- `hdmi-ui`: o requisito **"Layout responsivo à resolução do monitor"** passa a exigir (a) **escala tipográfica** proporcional à resolução, não só realocação por peso, e (b) **omissão de teclado e histórico** abaixo de limiares declarados, com a decisão tomada no arranque. O cenário de redimensionamento manual é substituído por um que descreve o comportamento real (tamanho fixado na construção).

## Impact

- **Código:** [software/ui/hdmi/app.py](../../../software/ui/hdmi/app.py) (constantes de fonte, `_build_layout`, visibilidade do teclado/rodapé) e um módulo novo em `software/ui/shared/` com a regra de faixas — puro, sem Tk, para ser testável sem display.
- **Testes:** novos casos em `software/tests/` cobrindo a escolha de faixa e o fator de escala como **funções puras** (sem abrir janela), evitando ampliar a superfície de testes que exigem Xvfb no CI.
- **Não afeta:** `software/core/` (motor), `software/accessibility/` (voz), o front do LCD (`ui/lcd/`, fixo em 800x480 por hardware) nem a seleção de saída (`hw_platform/display.py`, capability `display-switching`).
- **Acessibilidade:** o teclado físico continua sendo a entrada real (RF-05), então esconder o teclado na tela **não remove funcionalidade**; o catálogo de voz do PRD §13 não muda.

## Não-objetivos

- **Não** tornar a janela redimensionável nem reagir a `<Configure>` em runtime — foi decisão explícita manter a decisão no arranque.
- **Não** alterar o escopo matemático (PRD §5) nem qualquer comportamento do motor.
- **Não** mexer no front do LCD: a resolução dele é fixa pelo painel de 4,3".
- **Não** alterar a detecção/troca de saída de vídeo (RF-02/RF-09) — território da change `fix-dual-hdmi-exclusive-output`.
- **Não** remover o toggle manual do teclado: ele continua onde o teclado cabe.
