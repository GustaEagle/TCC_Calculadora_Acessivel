## ADDED Requirements

### Requirement: Repetir a última resposta completa

A calculadora SHALL permitir **reouvir e reexibir a última resposta completa** por meio de uma ação secundária do botão `=` (acionada com Ctrl ou Shift), sem introduzir um novo botão físico. A ação MUST NOT recalcular nem alterar a expressão atual.

#### Scenario: Repetir a última resposta por ação secundária
- **WHEN** existe um último resultado válido e o usuário aciona a ação secundária do `=` (Ctrl ou Shift + `=`)
- **THEN** o sistema anuncia por voz a última resposta completa
- **AND** exibe a última resposta sem recalcular

#### Scenario: Resposta completa mesmo com exibição truncada
- **WHEN** o último resultado foi truncado no display por limite de largura
- **THEN** a repetição anuncia o valor completo, não a versão truncada

#### Scenario: Sem resposta anterior
- **WHEN** o usuário aciona a repetição sem nenhum resultado válido na sessão
- **THEN** o sistema informa que não há resposta anterior (coerente com WRN-010)
- **AND** não altera a expressão atual
