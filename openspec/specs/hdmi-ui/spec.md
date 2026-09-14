# hdmi-ui Specification

## Purpose
TBD - created by archiving change add-hdmi-ui. Update Purpose after archive.

## Requirements

### Requirement: Front-end dedicado ao monitor HDMI
O sistema SHALL fornecer um front-end visual próprio para o monitor externo HDMI (`software/ui_hdmi/`), com layout projetado para tela maior (tipografia, área de histórico e alvo de foco/toque redimensionados), reutilizando o motor de cálculo de `software/core/` e o serviço de voz de `software/accessibility/speech.py` sem modificá-los.

#### Scenario: Inicialização no monitor
- **WHEN** o front-end HDMI é instanciado como saída ativa
- **THEN** ele exibe expressão e resultado usando `CalculatorState` de `software/core`, aciona `SpeechService` da mesma forma que o front do LCD (mesmas mensagens faladas, mesmo idioma pt-BR) e não importa nem duplica lógica de `software/core/engine.py`.

#### Scenario: Layout distinto do LCD, não escalado
- **WHEN** o front-end HDMI monta sua interface
- **THEN** ele usa dimensões, fontes e composição próprias (não uma cópia esticada de `ui_lcd/app.py`), aproveitando o espaço extra do monitor para mostrar mais histórico e/ou controles visíveis simultaneamente.

### Requirement: Layout responsivo à resolução do monitor

O front-end HDMI SHALL adaptar seu layout à resolução real reportada pelo sistema **na inicialização**, em vez de assumir uma resolução-alvo fixa. A adaptação MUST cobrir duas dimensões:

1. **Escala tipográfica** — tamanhos de fonte, espaçamentos e limites de truncamento do display SHALL derivar da resolução ativa, por um fator de escala com piso e teto (nunca texto ilegível por ser pequeno demais, nunca letras que estourem o painel).
2. **Composição por faixa de tamanho** — o front SHALL escolher uma entre três composições, conforme a resolução couber ou não em cada limiar declarado:
   - **completa**: expressão, resultado, teclado na tela e painel de histórico;
   - **média**: expressão, resultado e teclado — **sem** painel de histórico;
   - **compacta**: apenas expressão e resultado — **sem** teclado e **sem** histórico.

Os limiares MUST ser declarados em um único ponto do código (constantes nomeadas), não espalhados pela montagem da interface. Quando uma faixa omite o teclado, o controle de alternar teclado MUST ser omitido junto — a interface não pode oferecer uma ação que não tem efeito, inclusive para navegação por Tab e para os anúncios de voz.

A decisão de faixa e de escala SHALL ser tomada **uma única vez**, na construção da janela. A janela permanece de tamanho fixo (não redimensionável), então não há recomposição em tempo de execução.

Omitir teclado ou histórico MUST NOT reduzir o catálogo de operações (PRD §5) nem a entrada pelo teclado físico (RF-05): a calculadora continua plenamente operável na faixa compacta.

#### Scenario: Monitor com resolução diferente do padrão

- **WHEN** o front-end HDMI é iniciado em um monitor com resolução diferente de outras já testadas (ex.: 1366x768 em vez de 1920x1080)
- **THEN** os elementos da interface se realocam proporcionalmente ao espaço disponível (sem cortar, sobrepor ou deixar áreas vazias fixas desproporcionais) e as fontes acompanham a resolução, sem exigir alteração de código para essa resolução

#### Scenario: Monitor grande mostra a composição completa

- **WHEN** a resolução ativa atinge o limiar da faixa completa
- **THEN** a interface apresenta expressão, resultado, teclado na tela e painel de histórico, e o controle de alternar teclado está disponível

#### Scenario: Monitor intermediário esconde o histórico

- **WHEN** a resolução ativa atinge o limiar do teclado mas não o do histórico
- **THEN** a interface apresenta expressão, resultado e teclado, o painel de histórico não é montado, e nenhuma área vazia é reservada no lugar dele

#### Scenario: Monitor pequeno mostra apenas o display

- **WHEN** a resolução ativa fica abaixo do limiar do teclado
- **THEN** a interface apresenta apenas expressão e resultado, sem teclado, sem histórico e sem o controle de alternar teclado

#### Scenario: Escala tipográfica limitada nos extremos

- **WHEN** a resolução ativa é muito maior ou muito menor que a resolução de referência do layout
- **THEN** o fator de escala é limitado pelo piso e pelo teto declarados, de modo que a tipografia permanece legível sem estourar o painel

#### Scenario: Operação preservada na faixa compacta

- **WHEN** o front-end HDMI está na faixa compacta (sem teclado na tela)
- **THEN** todas as operações do catálogo do PRD §5 continuam acessíveis pelo teclado físico e os anúncios de voz seguem o mesmo catálogo de mensagens dos demais fronts

#### Scenario: Monitor ligado depois do boot mede o painel novo

- **WHEN** o monitor externo é conectado com a calculadora já em uso (RF-09) e o front do monitor é construído logo após a troca de saída
- **THEN** a faixa e a escala são calculadas a partir da resolução do **painel novo**, e não de um valor de tela obtido antes da troca

#### Scenario: Tamanho fixado na construção

- **WHEN** a janela do front-end HDMI já foi construída
- **THEN** a faixa e a escala escolhidas permanecem as mesmas durante toda a execução daquele front, sem recomposição em tempo de execução

### Requirement: Paridade de acessibilidade entre fronts
Toda entrada e resultado anunciados pelo front-end HDMI SHALL seguir o mesmo catálogo de mensagens e prioridades de erro do PRD §13 usado pelo front do LCD (mesmo código → mesmo significado em UI e voz).

#### Scenario: Erro de domínio no monitor
- **WHEN** uma operação inválida ocorre com o front-end HDMI ativo (ex.: divisão por zero)
- **THEN** a UI do monitor exibe o mesmo código de erro (`ERR-0xx`/`WRN-0xx`) e o TTS anuncia o mesmo prefixo de prioridade ("Erro"/"Aviso") que o front do LCD anunciaria para o mesmo erro.

#### Scenario: Entrada exclusivamente por teclado físico
- **WHEN** o front-end HDMI está ativo
- **THEN** ele aceita entrada apenas do teclado físico mapeado por `software/hw_platform/keyboard.py` (RF-05), sem exigir mouse ou toque na tela para operação completa.
