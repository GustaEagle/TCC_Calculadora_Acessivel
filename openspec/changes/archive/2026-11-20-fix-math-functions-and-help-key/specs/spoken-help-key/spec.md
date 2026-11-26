## ADDED Requirements

### Requirement: A tecla ? tem função no catálogo de teclas

A tecla `?` da matriz 6x7 (`SW25`, `C0L4`) SHALL ser mapeada para o token de ação `HELP`. `entry_for_keycap("?")` SHALL devolver essa entrada e SHALL NOT devolver `None`.

A `?` SHALL deixar de ser tratada como tecla sem função. O caminho de tecla não mapeada e o anúncio `NO_FUNCTION_SPEECH` SHALL permanecer no código apenas para teclas genuinamente desconhecidas (keycap fora do mapa, defeito de hardware).

A `?` SHALL NOT ganhar botão no teclado da tela: a posição que ela ocupa continua espaçador, e a consulta é função exclusiva do teclado físico. No teclado de PC, a tecla `?` SHALL ser mapeada para o mesmo token.

#### Scenario: Keycap da matriz resolve para o token de consulta

- **WHEN** `entry_for_keycap("?")` é chamado
- **THEN** a função primária devolvida é o token `HELP`

#### Scenario: Teclas genuinamente desconhecidas continuam anunciadas

- **WHEN** um evento de tecla chega com um keycap que não existe no mapa
- **THEN** o front anuncia `NO_FUNCTION_SPEECH`, preservando o retorno sonoro para quem não vê a tela

#### Scenario: Sem botão de consulta na tela

- **WHEN** os rótulos do teclado da tela são enumerados
- **THEN** `?` SHALL NOT constar entre eles

#### Scenario: A ? é alcançável pelo teclado de PC

- **WHEN** a tecla `?` é pressionada no teclado de PC
- **THEN** o token entregue ao front é `HELP`

### Requirement: A ? é um modificador de consulta de uso único

Pressionar `?` SHALL armar o **modo de consulta**: o sistema anuncia «Ajuda. Pressione uma tecla.» e acende o indicador `AJUDA`. A **próxima** tecla SHALL ser **descrita** em vez de executada, e o modo SHALL desligar-se sozinho depois dela.

O modo é um **toggle**, como o `Ctrl` e o `Shift`, e SHALL NOT exigir segurar a `?`: o scanner varre a matriz coluna a coluna e não identifica duas teclas pressionadas ao mesmo tempo, então "segurar e pressionar" não é possível no hardware do produto.

Pressionar `?` com o modo já armado SHALL **cancelá-lo**, anunciando «Ajuda cancelada.» e apagando o indicador. A tecla pressionada a seguir volta a ser executada normalmente.

#### Scenario: A ? arma o modo

- **WHEN** a tecla `?` é pressionada com o modo desarmado
- **THEN** o modo de consulta fica ativo, o indicador `AJUDA` acende, o anúncio é «Ajuda. Pressione uma tecla.» e a expressão permanece inalterada

#### Scenario: A tecla seguinte é descrita e não inserida

- **WHEN** a expressão é `"7"` e o utilizador pressiona `?` e depois `log`
- **THEN** a expressão continua a ser `"7"`, e a voz descreve as funções da tecla `log`

#### Scenario: Um dígito depois da ? é descrito e não digitado

- **WHEN** a expressão está vazia e o utilizador pressiona `?` e depois `7`
- **THEN** a expressão continua vazia e a voz descreve a tecla `7`

#### Scenario: O modo é de uso único

- **WHEN** o utilizador pressiona `?`, depois `7`, depois `8`
- **THEN** o `7` é descrito e a expressão passa a ser `"8"`, porque o modo desligou-se depois da primeira tecla

#### Scenario: Segunda ? cancela o modo

- **WHEN** o utilizador pressiona `?` duas vezes
- **THEN** o modo fica desarmado, o anúncio é «Ajuda cancelada.» e uma tecla pressionada a seguir é executada normalmente

### Requirement: A descrição anuncia as três funções da tecla

A descrição de uma tecla SHALL ter a forma «**Função [principal]. Com Controle ativo, função [Ctrl]. Com Shift ativo, função [Shift].**». Uma camada sem função SHALL ser anunciada como «Nenhuma».

Todos os nomes SHALL sair de `SPOKEN_TOKEN_NAMES`, a mesma fonte que a tecla usa quando é acionada a sério, para a descrição não poder divergir do comportamento real. Nenhum token de ação SHALL ser lido pelo nome cru: `=` e `RECALL` SHALL ter nomes falados («calcular» e «última resposta»). Os dígitos ficam de fora desta regra, porque o motor de voz já os lê como números.

A descrição SHALL ser uma função pura, partilhada pelos dois fronts e pelo modo somente áudio.

#### Scenario: Tecla com as três camadas

- **WHEN** a tecla `log` é descrita
- **THEN** o texto menciona «logaritmo decimal», «logaritmo natural» e «logaritmo na base x»

#### Scenario: Tecla sem funções secundárias

- **WHEN** a tecla `√` é descrita
- **THEN** o texto menciona «raiz quadrada» e a palavra «Nenhuma» aparece duas vezes

#### Scenario: Tecla de atalhos

- **WHEN** a tecla `Ans` é descrita
- **THEN** o texto menciona «resposta anterior», «histórico» e «ler a expressão atual», que são os atalhos dela

#### Scenario: Toda tecla da matriz é descritível

- **WHEN** cada um dos 38 switches da matriz é descrito
- **THEN** a descrição é não vazia e nenhum token de ação sem nome falado é lido pelo nome cru

### Requirement: A consulta não altera a expressão nem o estado

O modo de consulta SHALL NOT inserir nenhum caractere na linha de cálculo e SHALL NOT alterar o resultado apresentado, o `Ans`, o histórico, o modo angular, o volume nem o estado das telas. A tecla consultada SHALL NOT ser executada.

Os modificadores SHALL ser descritos como qualquer outra tecla: `?` seguido de `Ctrl` ou de `Shift` descreve o modificador, e SHALL NOT armá-lo.

#### Scenario: Estado intacto depois da consulta

- **WHEN** existe um resultado anterior e o utilizador pressiona `?` e depois `Shift`
- **THEN** o resultado apresentado, o `Ans`, o modo angular e o volume permanecem inalterados

#### Scenario: Modificador descrito não é armado

- **WHEN** o utilizador pressiona `?` e depois `Ctrl`
- **THEN** o `Ctrl` é descrito e o estado `CTRL` permanece desligado

### Requirement: Paridade da consulta entre os fronts e o modo somente áudio

A consulta SHALL produzir a mesma descrição no front do LCD, no front do monitor externo e em modo somente áudio, mantendo a paridade de acessibilidade entre fronts e o catálogo de operações sem redução (RF-04, RF-10). No front do monitor externo, o antigo atalho `Ctrl` + `Shift` ligados em simultâneo SHALL continuar a produzir a mesma descrição.

#### Scenario: Mesma descrição nos dois fronts

- **WHEN** o utilizador pressiona `?` e depois `Ans` no front do LCD e no front do monitor externo
- **THEN** o texto anunciado é o mesmo nos dois casos

#### Scenario: Consulta disponível sem vídeo

- **WHEN** a consulta é usada com o sistema em `DisplayMode.AUDIO_ONLY`
- **THEN** a descrição é produzida normalmente, por ser a única via de descoberta das funções sem a tela
