## MODIFIED Requirements

### Requirement: Entrega das teclas aos fronts visuais

Cada pressionamento SHALL ser entregue ao front visual ativo (LCD ou HDMI) **no laço de eventos do Tk**, nunca a partir da thread de varredura, e SHALL percorrer o mesmo tratamento de tokens do teclado de PC: modificadores `Ctrl`/`Shift`, histórico, blackout e anúncios por voz. O keycap SHALL ser resolvido para a entrada completa do catálogo de teclas (função primária, função com `Ctrl` e função com `Shift`), para que as funções secundárias funcionem pela matriz. Eventos de soltura SHALL NOT gerar tokens.

A tecla `?` (`SW25`, `C0L4`) SHALL ser entregue ao front como o token de consulta `HELP`, e SHALL NOT inserir nada na expressão. Pressionada, arma o modo de consulta «o que faz esta tecla?» (ver a capacidade `spoken-help-key`). Apenas um keycap **fora do mapa** (tecla desconhecida, defeito de hardware) SHALL ser anunciado como tecla sem função.

Quando o ambiente não oferecer a matriz (PC, CI, pacote `gpiod` ausente ou `--keypad-matrix off`), a aplicação SHALL arrancar normalmente, apenas com o teclado de PC.

#### Scenario: Tecla da matriz chega ao front
- **WHEN** o utilizador pressiona a tecla `7` da matriz com o front LCD ativo
- **THEN** o `7` é inserido na expressão e anunciado por voz, exatamente como no teclado de PC

#### Scenario: Função secundária pela matriz
- **WHEN** o utilizador pressiona `Ctrl` e depois `sen` na matriz
- **THEN** a função inserida é o arco seno (`asin(`) e o `Ctrl` é consumido

#### Scenario: Soltura não gera entrada
- **WHEN** uma tecla da matriz é solta
- **THEN** nada é inserido na expressão e nada é anunciado

#### Scenario: Tecla de consulta
- **WHEN** o utilizador pressiona a tecla `?` da matriz
- **THEN** a expressão permanece inalterada, o modo de consulta fica armado e o front anuncia «Ajuda. Pressione uma tecla.»

#### Scenario: Tecla sem função
- **WHEN** a matriz entrega um evento cujo keycap não consta do mapa (tecla desconhecida ou defeito de hardware; a `?` já NÃO é um destes casos)
- **THEN** a expressão permanece inalterada e o front anuncia que a tecla não tem função

#### Scenario: Aplicação sem matriz disponível
- **WHEN** a aplicação arranca num PC, sem `gpiod` instalado ou sem `gpiochip0`
- **THEN** o front abre normalmente com o teclado de PC, e o log registra que a matriz não está ativa
