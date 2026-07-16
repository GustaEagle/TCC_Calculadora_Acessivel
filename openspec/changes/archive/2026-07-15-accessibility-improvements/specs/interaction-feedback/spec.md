## ADDED Requirements

### Requirement: Indicação de estado dos elementos

Os elementos interativos SHALL comunicar seus estados — **foco**, **pressionado** e **selecionado/ativo** — por canal visual e/ou sonoro, para que o usuário perceba onde está e o que acionou sem depender exclusivamente da visão.

#### Scenario: Elemento em foco é perceptível
- **WHEN** o foco chega a um botão via teclado
- **THEN** há indicação visual distinta de foco
- **AND** opcionalmente um retorno sonoro identificando o elemento focado

#### Scenario: Acionamento é confirmado
- **WHEN** um botão é pressionado
- **THEN** há indicação visual de estado pressionado
- **AND** um retorno sonoro confirma a ação

### Requirement: Estado de modificador visível e audível

O estado ativo de modificadores (Ctrl, Shift) e do modo de ângulo SHALL ser refletido simultaneamente na interface visual e no áudio ao mudar.

#### Scenario: Modificador ativo é indicado nos dois canais
- **WHEN** o usuário ativa Ctrl ou Shift
- **THEN** um indicador visual mostra o modificador ativo
- **AND** o sistema anuncia a mudança de estado por voz

#### Scenario: Rótulos secundários refletem o modificador
- **WHEN** um modificador está ativo
- **THEN** os rótulos dos botões afetados mostram a função secundária correspondente
