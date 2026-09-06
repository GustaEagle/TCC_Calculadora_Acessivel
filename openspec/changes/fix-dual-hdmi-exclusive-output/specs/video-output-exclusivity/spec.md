## Purpose

Garantir que a decisão de saída do PRD §7 seja de facto aplicada ao servidor X: em qualquer combinação de portas HDMI reconhecidas, exatamente uma saída de vídeo fica ativa, desde o arranque da sessão gráfica, com verificação do resultado e diagnóstico quando a reconfiguração falha.

## ADDED Requirements

### Requirement: Exatamente uma saída de vídeo ativa
Sempre que houver ao menos uma saída de vídeo utilizável, o sistema SHALL deixar ativa no servidor X **apenas** a saída correspondente ao `DisplayMode` escolhido pelo `DisplaySelector`, desligando todas as demais. O sistema SHALL NOT deixar duas saídas ativas simultaneamente, seja em modo estendido ou espelhado (PRD §7.2, RF-03).

#### Scenario: LCD e monitor externo reconhecidos ao mesmo tempo
- **WHEN** o layout de vídeo é aplicado com o modo `DisplayMode.HDMI`
- **THEN** a saída X do monitor externo é ligada e marcada como primária, e a saída X do LCD é desligada na mesma invocação do `xrandr`

#### Scenario: Apenas o LCD reconhecido
- **WHEN** o layout de vídeo é aplicado com o modo `DisplayMode.LCD`
- **THEN** a saída X do LCD é ligada e marcada como primária, e a saída X do monitor externo é desligada

#### Scenario: Sem vídeo utilizável
- **WHEN** o layout de vídeo é aplicado com o modo `DisplayMode.AUDIO_ONLY`
- **THEN** nenhuma chamada de reconfiguração de saída é feita e o sistema segue para a operação somente-áudio

### Requirement: Layout exclusivo aplicado antes de qualquer UI aparecer
O sistema SHALL fornecer um modo de execução que resolve e aplica o layout exclusivo de vídeo **sem** instanciar nenhum front visual, para que a sessão gráfica possa aplicá-lo antes de subir a interface. A sessão gráfica do kiosk SHALL invocar esse modo antes de arrancar o app, de forma que um desktop estendido autoconfigurado pelo X nunca chegue a ficar visível.

#### Scenario: Arranque com as duas portas HDMI ligadas
- **WHEN** a sessão gráfica arranca com o LCD e o monitor externo ambos conectados
- **THEN** o layout exclusivo com o monitor como única saída ativa é aplicado antes de a janela da calculadora ser criada, e em nenhum momento as duas telas mostram parte da área de trabalho

#### Scenario: Modo de aplicação de layout não abre janela
- **WHEN** o entrypoint é executado no modo de aplicação de layout
- **THEN** nenhum front visual (`ui/lcd` ou `ui/hdmi`) é instanciado e o processo encerra após aplicar o layout

### Requirement: Nomes de saída X descobertos, não adivinhados
O sistema SHALL determinar o nome de cada saída no `xrandr` a partir das saídas realmente presentes no servidor X, e não apenas por convenção de nomes. A resolução SHALL seguir a precedência: variável de ambiente explícita, depois correspondência com uma saída presente no X, depois a convenção `HDMI-A-N` → `HDMI-N` como último recurso.

#### Scenario: Kernel usa uma convenção de nomes diferente
- **WHEN** o conector DRM é `HDMI-A-2` e o servidor X expõe a saída como `HDMI2` (sem hífen)
- **THEN** o sistema usa `HDMI2` na chamada do `xrandr`, em vez de falhar com o nome `HDMI-2` da convenção

#### Scenario: Variável de ambiente tem precedência
- **WHEN** `CALC_MONITOR_XRANDR_OUTPUT` está definida
- **THEN** o valor da variável é usado, mesmo que o servidor X exponha outra saída que casaria com a convenção

#### Scenario: Sem servidor X disponível
- **WHEN** a descoberta é tentada numa máquina sem `DISPLAY` ou sem `xrandr` (máquina de desenvolvimento ou CI)
- **THEN** a resolução recai na convenção sem erro, e nenhuma reconfiguração é tentada

### Requirement: Resultado da reconfiguração é verificado
Após aplicar o layout, o sistema SHALL reler o estado das saídas do servidor X e confirmar que apenas a saída alvo está ativa. O sistema SHALL NOT tratar o código de saída do `xrandr` como prova suficiente de que o layout foi aplicado.

#### Scenario: Reconfiguração bem-sucedida
- **WHEN** o layout é aplicado e a releitura mostra apenas a saída alvo ativa
- **THEN** a operação é reportada como bem-sucedida

#### Scenario: xrandr aceita o comando mas o LCD continua ativo
- **WHEN** o `xrandr` retorna sucesso mas a releitura mostra o LCD ainda ativo junto com o monitor
- **THEN** a operação é reportada como falhada, e não como bem-sucedida

### Requirement: Falha de layout é diagnosticável sem desmontar o kiosk
Quando o layout exclusivo não puder ser aplicado ou verificado, o sistema SHALL registrar a ocorrência como **WRN-012** (PRD §13) com o modo pretendido e os nomes de saída usados, num destino persistente e legível na imagem do produto. A interface SHALL continuar a arrancar apesar da falha, e o sistema SHALL NOT anunciar a falha por voz (WRN-012 é P2 e o anúncio é opcional; a fala reservada ao RF-09 é a troca de tela, não a falha de layout).

#### Scenario: Nome de saída inexistente no servidor X
- **WHEN** a reconfiguração falha porque nenhuma saída do X corresponde ao conector configurado
- **THEN** um registro WRN-012 é gravado com o modo pretendido e os nomes tentados, e o front correspondente ao modo é iniciado normalmente

#### Scenario: Falha de vídeo não bloqueia a calculadora
- **WHEN** a aplicação do layout falha por qualquer motivo
- **THEN** a calculadora continua operável, com o teclado e o feedback por voz funcionando (RF-04, RF-08)

### Requirement: Diagnóstico de bring-up cobre DRM e X
O comando de diagnóstico de saídas SHALL listar, numa única execução, os conectores DRM com o seu estado, as saídas conhecidas pelo servidor X, e o mapeamento efetivo de cada papel (LCD, monitor) para o conector DRM e para a saída X que serão realmente usados.

#### Scenario: Bring-up na imagem do Raspberry Pi
- **WHEN** o comando de diagnóstico é executado na sessão gráfica do kiosk
- **THEN** a saída mostra os conectores DRM com estado, as saídas do `xrandr`, e para cada papel o par conector DRM / saída X em uso

#### Scenario: Diagnóstico numa máquina sem vídeo
- **WHEN** o comando é executado numa máquina sem conectores DRM e sem servidor X
- **THEN** o comando reporta a ausência de cada um deles e encerra sem erro

### Requirement: A janela ocupa o painel ativo
O front visual SHALL dimensionar a sua janela a partir da geometria da saída de vídeo ativa, e SHALL NOT assumir uma resolução fixa que possa deixá-la num canto de um framebuffer maior.

#### Scenario: Monitor externo com resolução maior que a janela padrão
- **WHEN** o front do monitor é iniciado numa saída de 1920x1080
- **THEN** a janela é dimensionada a partir dessa geometria, e não fixada em 1280x720
