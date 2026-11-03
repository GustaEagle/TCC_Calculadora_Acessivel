## ADDED Requirements

### Requirement: A tecla ? tem função no catálogo de teclas

A tecla `?` da matriz 6x7 (`SW25`, coordenada `C0L4`) SHALL ser mapeada para o token de atalho `HELP`. `entry_for_keycap("?")` SHALL devolver essa entrada e SHALL NOT devolver `None`.

A `?` SHALL deixar de ser tratada como tecla sem função: o caminho de tecla não mapeada e o anúncio `NO_FUNCTION_SPEECH` SHALL permanecer no código apenas para teclas genuinamente desconhecidas (keycap fora do mapa, defeito de hardware), e a `?` SHALL NOT passar por ele.

A `?` SHALL NOT ganhar botão no teclado da tela: a posição que ela ocupa em `LEFT_BUTTONS` continua espaçador, e a ajuda é uma função exclusiva do teclado físico.

#### Scenario: Keycap da matriz resolve para o token de ajuda

- **WHEN** `entry_for_keycap("?")` é chamado
- **THEN** a função primária devolvida é o token `HELP`

#### Scenario: A ? deixa de ser tecla não mapeada

- **WHEN** a matriz emite um evento de pressionamento do switch `SW25` (`C0L4`)
- **THEN** o front trata o token `HELP` e SHALL NOT anunciar `NO_FUNCTION_SPEECH`

#### Scenario: Teclas genuinamente desconhecidas continuam anunciadas

- **WHEN** um evento de tecla chega com um keycap que não existe no mapa
- **THEN** o front anuncia `NO_FUNCTION_SPEECH`, preservando o retorno sonoro para quem não vê a tela

#### Scenario: Sem botão de ajuda na tela

- **WHEN** os rótulos do teclado da tela são enumerados
- **THEN** `?` SHALL NOT constar entre eles

### Requirement: A ajuda anuncia o modo angular e os atalhos do produto

Ao receber o token `HELP`, o sistema SHALL anunciar por voz, em pt-BR, o **modo angular ativo** (graus ou radianos) seguido dos **atalhos de teclado** disponíveis, cada um com a sua descrição e a combinação de teclas.

O texto de cada atalho SHALL ser derivado da **mesma fonte única** que define os atalhos em `ui/shared/keypad.py`, de modo que a ajuda não possa divergir dos atalhos realmente implementados. As combinações SHALL ser faladas pelos nomes do catálogo `SPOKEN_TOKEN_NAMES` (por exemplo, `Ctrl` + `Ans` é anunciado como "controle mais resposta anterior"), e SHALL NOT ser faladas como os rótulos visuais com símbolos `+` e `/`.

A ajuda SHALL cobrir, no mínimo, todos os atalhos declarados: histórico, leitura da expressão atual, volume, e apagar/religar as telas.

#### Scenario: Conteúdo da ajuda em modo graus

- **WHEN** a tecla `?` é pressionada com o modo angular em `deg`
- **THEN** o anúncio começa por identificar a ajuda e o modo graus, e inclui os quatro atalhos com as respetivas combinações faladas

#### Scenario: Conteúdo da ajuda em modo radianos

- **WHEN** a tecla `?` é pressionada com o modo angular em `rad`
- **THEN** o anúncio identifica o modo radianos

#### Scenario: Cobertura de todos os atalhos declarados

- **WHEN** o texto da ajuda é gerado
- **THEN** existe uma entrada para cada atalho declarado em `ui/shared/keypad.py` (histórico, ler expressão, volume, telas), de forma que acrescentar um atalho sem o acrescentar à ajuda SHALL falhar nos testes

#### Scenario: Combinações faladas por nome, não por símbolo

- **WHEN** o texto da ajuda é gerado
- **THEN** o texto SHALL NOT conter os caracteres `+` ou `/` como representação de teclas, usando em vez disso os nomes de `SPOKEN_TOKEN_NAMES`

### Requirement: A ajuda é interrompível e não bloqueia a entrada

Pressionar a tecla `?` **enquanto a ajuda está a ser falada** SHALL interromper a fala. Qualquer outra tecla pressionada durante a ajuda SHALL igualmente interrompê-la e ser processada normalmente.

Nenhuma fala da ajuda SHALL bloquear a entrada por teclado de forma prolongada, conforme o RF-08: o anúncio usa a política de interrupção já existente no `SpeechService`.

#### Scenario: Segundo toque na ? interrompe a ajuda

- **WHEN** a tecla `?` é pressionada e, durante o anúncio, é pressionada novamente
- **THEN** a fala em curso é interrompida e a ajuda SHALL NOT ser reproduzida duas vezes em simultâneo

#### Scenario: Outra tecla interrompe a ajuda e é processada

- **WHEN** a tecla `?` é pressionada e, durante o anúncio, o utilizador pressiona `7`
- **THEN** a fala da ajuda é interrompida, o dígito `7` é inserido na expressão e o seu nome é anunciado

#### Scenario: Entrada aceita durante a ajuda

- **WHEN** a ajuda está a ser falada
- **THEN** o laço de entrada continua a aceitar teclas, sem espera pelo fim do anúncio (RF-08)

### Requirement: A ajuda não altera a expressão nem o estado de cálculo

O token `HELP` SHALL NOT inserir qualquer caractere na linha de cálculo, SHALL NOT alterar o resultado apresentado, o `Ans`, o histórico, o modo angular, o volume nem o estado das telas. É uma ação exclusivamente informativa.

Os modificadores `Ctrl` e `Shift` SHALL ser consumidos como em qualquer outra tecla, sem efeito adicional sobre a ajuda.

#### Scenario: Expressão intacta depois da ajuda

- **WHEN** a expressão na linha de cálculo é `"5 nCr 2"` e a tecla `?` é pressionada
- **THEN** a expressão continua a ser `"5 nCr 2"` e nenhum token é acrescentado

#### Scenario: Resultado e Ans intactos depois da ajuda

- **WHEN** existe um resultado anterior e a tecla `?` é pressionada
- **THEN** o resultado apresentado e o valor de `Ans` permanecem inalterados

#### Scenario: Modo angular intacto depois da ajuda

- **WHEN** o modo angular é `deg` e a tecla `?` é pressionada
- **THEN** o modo angular continua a ser `deg`, apesar de a ajuda o anunciar

### Requirement: Paridade da ajuda entre os fronts e o modo somente áudio

A tecla `?` SHALL produzir o mesmo anúncio no front do LCD, no front do monitor externo e em modo somente áudio, mantendo a paridade de acessibilidade entre fronts e o catálogo de operações sem redução (RF-04, RF-10).

#### Scenario: Mesma ajuda nos dois fronts visuais

- **WHEN** a tecla `?` é pressionada no front do LCD e no front do monitor externo
- **THEN** o texto anunciado é o mesmo nos dois casos

#### Scenario: Ajuda disponível sem vídeo

- **WHEN** a tecla `?` é pressionada com o sistema em `DisplayMode.AUDIO_ONLY`
- **THEN** o anúncio é produzido normalmente, por ser a única via de descoberta dos atalhos sem a tela
