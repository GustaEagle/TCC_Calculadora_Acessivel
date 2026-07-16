## ADDED Requirements

### Requirement: Mensagens claras preservando o código

As mensagens de erro e aviso SHALL usar linguagem clara e objetiva em português (Brasil), preservando o **código** e o significado definidos no PRD §13. O mesmo código MUST produzir a mesma categoria e sentido na UI e no TTS.

#### Scenario: Erro exibido de forma clara com código estável
- **WHEN** o motor retorna um erro (ex.: ERR-001)
- **THEN** a UI mostra uma mensagem clara e objetiva associada àquele código
- **AND** o código permanece o mesmo definido no PRD §13

#### Scenario: TTS e UI coerentes para o mesmo código
- **WHEN** um erro é comunicado por voz e por texto
- **THEN** ambos os canais referem-se ao mesmo código e ao mesmo significado

### Requirement: Prioridade refletida no feedback

Erros de prioridade **P1** SHALL bloquear/realçar o resultado e ter precedência de anúncio; avisos **P2** SHALL informar sem bloquear a operação, conforme o PRD §13.

#### Scenario: Erro P1 tem precedência de anúncio
- **WHEN** um erro P1 ocorre com anúncios de menor prioridade pendentes
- **THEN** o erro P1 é anunciado com precedência

#### Scenario: Aviso P2 não bloqueia a operação
- **WHEN** um aviso P2 é emitido (ex.: WRN-010)
- **THEN** o usuário é informado
- **AND** pode continuar a operação
