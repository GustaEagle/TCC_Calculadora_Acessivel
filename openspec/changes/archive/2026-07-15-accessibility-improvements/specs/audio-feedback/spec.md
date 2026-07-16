## ADDED Requirements

### Requirement: Interrupção determinística da fala

O serviço de voz SHALL garantir que um anúncio de maior prioridade (ex.: resultado ou erro P1) **interrompa** de forma consistente qualquer anúncio em curso ou enfileirado de menor prioridade, atendendo ao RF-08. Após uma interrupção, apenas o anúncio mais recente MUST ser reproduzido.

#### Scenario: Resultado interrompe anúncio de tecla
- **WHEN** uma tecla está sendo anunciada e o usuário aciona a avaliação
- **THEN** o anúncio da tecla é cortado
- **AND** o resultado é falado sem esperar o término do anúncio anterior

#### Scenario: Fila não acumula anúncios obsoletos
- **WHEN** várias teclas são pressionadas em sucessão rápida
- **THEN** anúncios antigos não reproduzidos são descartados quando um anúncio de maior prioridade chega
- **AND** o usuário não ouve uma fila longa e atrasada de anúncios

### Requirement: Cobertura sonora de todos os elementos interativos

Todo elemento interativo SHALL ter retorno sonoro adequado e consistente: teclas numéricas e de operação, modificadores (Ctrl, Shift), alternância de modo (graus/radianos), abertura de histórico e ações de navegação.

#### Scenario: Modificadores anunciam estado
- **WHEN** o usuário ativa ou desativa Ctrl ou Shift
- **THEN** o sistema anuncia o novo estado do modificador

#### Scenario: Ação sem som é corrigida
- **WHEN** qualquer elemento interativo é acionado
- **THEN** existe um anúncio de voz correspondente à ação

### Requirement: Leitura correta de resultado e símbolos

O TTS SHALL anunciar corretamente o **resultado** das operações e os **símbolos** inseridos pelo usuário, usando nomes em português (Brasil) inteligíveis.

#### Scenario: Símbolo é lido pelo nome
- **WHEN** o usuário insere um operador ou função
- **THEN** o anúncio usa o nome falado correspondente (ex.: "dividido por", "raiz quadrada")

#### Scenario: Resultado é lido por extenso da forma exibida
- **WHEN** uma avaliação bem-sucedida ocorre
- **THEN** o sistema anuncia o resultado correspondente ao valor exibido
