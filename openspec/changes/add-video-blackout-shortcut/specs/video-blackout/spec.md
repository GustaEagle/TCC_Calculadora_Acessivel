## Purpose

Permitir que o utilizador apague e religue, por comando de teclado, todas as saídas de vídeo reconhecidas, poupando bateria do UPS e preservando a privacidade do ecrã, sem interromper a calculadora — que permanece plenamente operável por teclado e voz (RF-04, RF-05, RF-06).

## ADDED Requirements

### Requirement: Comando de teclado apaga todas as saídas de vídeo

O sistema SHALL oferecer um comando de teclado, disponível tanto no teclado físico do produto como no teclado de PC, que desliga **todas** as saídas de vídeo atualmente reconhecidas. Quando o monitor externo estiver conectado, ele SHALL ser desligado junto com o LCD; quando não estiver, o comando SHALL desligar apenas o LCD e ainda assim ser considerado bem-sucedido.

O comando SHALL usar apenas teclas que existem na matriz 6x7 do produto e SHALL NOT deslocar nenhuma função do catálogo matemático do PRD §5. O comando é a combinação `Ctrl` + `AC` — a função secundária de `AC` —, idêntica no teclado de PC com `Ctrl` + `Esc`. Como toda a função secundária, SHALL substituir a função primária de `AC`: a expressão em curso SHALL NOT ser limpa pelo comando.

#### Scenario: Atalho com as teclas da matriz
- **WHEN** o utilizador pressiona `Ctrl` e em seguida `AC`, no teclado físico ou no de PC (`Esc`)
- **THEN** o comando de vídeo é executado, o `Ctrl` é consumido, e a expressão em curso permanece intacta

#### Scenario: LCD e monitor externo ambos conectados
- **WHEN** o utilizador aciona o comando de vídeo e as duas saídas HDMI estão reconhecidas
- **THEN** ambas as saídas ficam inativas e nenhuma imagem é apresentada em qualquer painel

#### Scenario: Apenas o LCD conectado
- **WHEN** o utilizador aciona o comando de vídeo e apenas a saída do LCD está reconhecida
- **THEN** a saída do LCD fica inativa e o comando é reportado como bem-sucedido, sem erro pela ausência do monitor

#### Scenario: Atalho escolhido não colide com o catálogo matemático
- **WHEN** o catálogo de teclas do produto é consultado
- **THEN** o comando de vídeo não substitui nenhum token de operação, função científica, dígito ou separador definido no PRD §5, e nenhuma tecla inexistente na matriz é necessária para o acionar

### Requirement: Calculadora permanece operável com as telas apagadas

Com as saídas de vídeo apagadas, o sistema SHALL continuar a aceitar entrada pelo teclado, a avaliar expressões e a anunciar resultados por voz, exatamente como antes do comando. O front ativo SHALL NOT ser destruído nem substituído pelo laço somente-áudio: o estado de blackout é uma **preferência do utilizador**, distinta de `DisplayMode.AUDIO_ONLY`, que designa ausência de hardware de vídeo utilizável.

A expressão em curso, o valor de `Ans`, o histórico da sessão e o modo graus/radianos SHALL permanecer inalterados ao apagar e ao religar.

#### Scenario: Cálculo completo com as telas apagadas
- **WHEN** o utilizador apaga as telas e em seguida digita uma expressão e a avalia
- **THEN** o resultado é calculado e anunciado por voz, e passa a integrar o histórico da sessão

#### Scenario: Estado preservado através do ciclo apagar/religar
- **WHEN** o utilizador tem uma expressão parcialmente digitada, apaga as telas e depois as religa
- **THEN** a mesma expressão parcial, o mesmo `Ans`, o mesmo histórico e o mesmo modo graus/radianos continuam em vigor e são apresentados no painel que reacendeu

#### Scenario: Blackout não é confundido com ausência de vídeo
- **WHEN** as telas estão apagadas por comando do utilizador
- **THEN** o modo de operação continua a ser o front visual correspondente ao painel reconhecido, e o sistema SHALL NOT passar a operar como `DisplayMode.AUDIO_ONLY`

### Requirement: Confirmação falada em ambos os sentidos

Como o utilizador fica sem qualquer retorno visual, o sistema SHALL anunciar por voz cada acionamento do comando, tanto ao apagar como ao religar, usando o código de aviso **WRN-013** registado no PRD §13.

O anúncio de desligamento SHALL nomear explicitamente a tecla que reacende as telas, por ser a única informação que permite desfazer a ação sem ver o ecrã.

O sistema SHALL NOT reutilizar o código WRN-012 para este comando, uma vez que esse código já designa a troca automática de saída do RF-09 e a mesma frase não pode ter dois significados.

#### Scenario: Anúncio ao apagar nomeia a via de retorno
- **WHEN** o utilizador aciona o comando e as telas se apagam
- **THEN** a voz anuncia o aviso 013 informando que as telas foram desligadas e indicando qual tecla as religa

#### Scenario: Anúncio ao religar
- **WHEN** o utilizador aciona o comando com as telas já apagadas
- **THEN** a voz anuncia o aviso 013 informando que a tela foi religada, identificando o painel que reacendeu

#### Scenario: Falha ao apagar é anunciada e não altera o estado
- **WHEN** o utilizador aciona o comando e a reconfiguração das saídas falha ou não é confirmada pela releitura do estado
- **THEN** a voz anuncia o aviso 013 informando que não foi possível desligar as telas, o estado permanece «aceso», e o sistema SHALL NOT anunciar um desligamento que não ocorreu

### Requirement: Recuperação garantida pela tecla AC

Quando as telas estiverem apagadas, a tecla `AC` SHALL religar a saída de vídeo, além do seu efeito habitual de limpar a expressão e o último resultado. Isto garante uma segunda via de recuperação para o utilizador que acione o comando por engano e não saiba, ou não recorde, qual tecla o desfaz.

Quando as telas estiverem acesas, `AC` SHALL manter exatamente o comportamento atual, sem qualquer efeito sobre o vídeo.

#### Scenario: AC reacende a tela
- **WHEN** as telas estão apagadas e o utilizador pressiona `AC`
- **THEN** a saída de vídeo apropriada é reativada e a expressão é limpa

#### Scenario: AC inalterado com a tela acesa
- **WHEN** as telas estão acesas e o utilizador pressiona `AC`
- **THEN** a expressão e o último resultado são limpos e nenhuma saída de vídeo é reconfigurada

### Requirement: Reacendimento respeita a prioridade de painel

Ao religar, o sistema SHALL escolher o painel pela regra de prioridade já vigente do PRD §7.2 — o monitor externo quando reconhecido, o LCD caso contrário — e SHALL manter exatamente uma saída ativa. O comando SHALL NOT memorizar qual painel estava aceso antes do blackout, de modo que uma troca de hardware ocorrida entretanto seja respeitada.

#### Scenario: Monitor ligado enquanto as telas estavam apagadas
- **WHEN** o utilizador apaga as telas tendo apenas o LCD, liga o monitor externo, e depois religa
- **THEN** a UI reacende no monitor externo e o LCD permanece apagado

#### Scenario: Monitor removido enquanto as telas estavam apagadas
- **WHEN** o utilizador apaga as telas tendo o monitor externo ativo, desliga o monitor, e depois religa
- **THEN** a UI reacende no LCD

### Requirement: A escolha sobrevive à troca automática de front

Se o estado das saídas de vídeo mudar enquanto as telas estiverem apagadas, disparando a entrega de front do RF-09, o front que assume SHALL nascer igualmente apagado. Uma reconfiguração de hardware SHALL NOT cancelar em silêncio uma escolha explícita do utilizador.

#### Scenario: Hotplug durante o blackout não reacende a tela
- **WHEN** as telas estão apagadas e o monitor externo é conectado, levando o sistema a entregar a UI ao outro front
- **THEN** o novo front assume com as saídas de vídeo ainda apagadas, sem qualquer painel a acender

### Requirement: Estado inicial e ausência de persistência

O sistema SHALL arrancar sempre com a saída de vídeo acesa. A preferência de blackout SHALL NOT ser persistida entre encerramentos, em coerência com o RF-06 e o RF-13, que dispensam persistência de sessão — garantindo que nenhum arranque possa apresentar-se ao utilizador como um aparelho sem imagem.

#### Scenario: Arranque após sessão encerrada em blackout
- **WHEN** o utilizador apaga as telas, encerra a calculadora e a inicia de novo
- **THEN** a calculadora arranca com a saída de vídeo ativa, apresentando a UI normalmente

### Requirement: Degradação segura sem servidor X

Em máquina sem servidor X ou sem a ferramenta de reconfiguração de saídas — o caso da máquina de desenvolvimento —, o comando SHALL registar a indisponibilidade e SHALL NOT interromper, bloquear ou fazer falhar a aplicação. O comportamento SHALL alinhar-se ao dos restantes caminhos de vídeo, que já tratam a ausência de X como melhor-esforço.

#### Scenario: Comando acionado em máquina de desenvolvimento
- **WHEN** o comando é acionado num ambiente sem servidor X disponível
- **THEN** nenhuma exceção é propagada, a ocorrência fica registada no log, e a calculadora continua a aceitar entrada e a responder por voz
