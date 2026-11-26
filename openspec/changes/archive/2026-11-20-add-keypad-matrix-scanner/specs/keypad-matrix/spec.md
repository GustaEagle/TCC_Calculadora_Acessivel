## Purpose

Ler a matriz física 6x7 do teclado da calculadora diretamente pelos GPIO do Raspberry Pi 4, sem microcontrolador intermediário (PRD §6). A leitura usa a pinagem e a polaridade validadas no hardware, aplica debounce (RF-11) e entrega cada tecla aos fronts visuais pelo mesmo caminho do teclado de PC, cumprindo a entrada exclusivamente pelo teclado físico (RF-05).

## ADDED Requirements

### Requirement: Pinagem validada da matriz

O sistema SHALL usar exatamente esta atribuição de GPIO, em numeração BCM, para os 13 condutores da matriz:

| Coluna | GPIO (BCM) | Pino físico J8 | Linha | GPIO (BCM) | Pino físico J8 |
| ------ | ---------- | -------------- | ----- | ---------- | -------------- |
| C0 | 26 | 37 | L0 | 10 | 19 |
| C1 | 19 | 35 | L1 | 9 | 21 |
| C2 | 13 | 33 | L2 | 11 | 23 |
| C3 | 21 | 40 | L3 | 17 | 11 |
| C4 | 20 | 38 | L4 | 27 | 13 |
| C5 | 15 | 10 | L5 | 22 | 15 |
| C6 | 14 | 8 | | | |

Os rótulos `C0..C6` e `L0..L5` SHALL ser 0-based e SHALL coincidir com as nets `Col0..Col6` e `Row0..Row5` do esquemático KiCad. O offset de linha no `gpiochip0` SHALL ser o número BCM. O pino físico SHALL ser usado apenas como informação de bancada e SHALL NOT ser passado ao `gpiod` como offset.

#### Scenario: Linhas no GPIO validado
- **WHEN** a pinagem da matriz é consultada
- **THEN** as linhas `L0..L5` estão, nesta ordem, em GPIO10, GPIO9, GPIO11, GPIO17, GPIO27 e GPIO22, e as colunas `C0..C6` em GPIO26, GPIO19, GPIO13, GPIO21, GPIO20, GPIO15 e GPIO14

#### Scenario: GPIO27 no pino físico 13
- **WHEN** a linha `L4` é descrita
- **THEN** ela aparece como GPIO27 no pino físico 13, e o pino físico 27 não pertence à matriz

#### Scenario: Pinagem inconsistente recusada na importação
- **WHEN** uma edição da pinagem repete um GPIO, põe um GPIO num pino físico que não é o dele no J8, ou ocupa GPIO2/GPIO3 (I2C1 do UPS HAT)
- **THEN** a importação do módulo de pinagem falha com uma mensagem que nomeia o condutor, antes de qualquer acesso ao hardware

### Requirement: Mapa de switches e keycaps

O sistema SHALL declarar os 38 switches `SW0..SW37`, cada um com a sua coordenada `C#L#` e o seu keycap, conforme a tabela validada no hardware (de `SW0 = C0L0 = Pol` até `SW37 = C6L5 = Del`). As coordenadas `C2L1`, `C2L2`, `C2L3` e `C4L4` SHALL ser declaradas como posições sem switch e SHALL NOT gerar keycap nem evento de tecla.

#### Scenario: Coordenada mapeada para switch e keycap
- **WHEN** o switch em `C3L1` é consultado
- **THEN** ele é o `SW9` e o seu keycap é `7`

#### Scenario: Posição sem switch
- **WHEN** a varredura detecta sinal numa posição sem switch (`C2L1`, `C2L2`, `C2L3` ou `C4L4`)
- **THEN** nenhum evento de tecla é emitido e o sistema registra um aviso de diagnóstico no log, emitido uma vez por ocorrência contínua

#### Scenario: Mapa consistente com a grade
- **WHEN** o módulo de pinagem é importado
- **THEN** existem exatamente 38 switches com coordenadas distintas, todas dentro da grade 7x6, e nenhuma coincide com as 4 posições vazias; caso contrário, a importação falha

### Requirement: Polaridade elétrica e invariantes de segurança

O sistema SHALL ler a matriz com esta configuração, validada no hardware:

- linhas: entrada com **pull-down**;
- coluna ativa: saída em **HIGH**, sem bias;
- colunas inativas: entrada **sem bias** (alta impedância).

Em nenhum momento duas colunas SHALL estar configuradas como saída ao mesmo tempo, e nenhuma linha SHALL ser configurada como saída pelo scanner. Cada reconfiguração SHALL especificar o estado de **todos** os 13 condutores, para que nenhuma linha perca o pull-down por um valor padrão implícito do kernel.

#### Scenario: Apenas uma coluna em saída
- **WHEN** uma varredura completa é executada
- **THEN** em cada configuração aplicada ao chip há no máximo uma coluna em saída, e todas as linhas estão em entrada com pull-down

#### Scenario: Coluna volta a flutuar entre ativações
- **WHEN** o scanner passa da coluna `Cn` para a coluna `Cn+1`
- **THEN** existe uma configuração intermediária em que `Cn` já está em entrada sem bias e `Cn+1` ainda não foi ativada

#### Scenario: Exceção durante a leitura não deixa a coluna ativa
- **WHEN** a leitura das linhas falha com exceção enquanto uma coluna está em HIGH
- **THEN** essa coluna é devolvida à entrada sem bias antes de a exceção se propagar

### Requirement: Varredura com estabilização

Para cada coluna, o sistema SHALL ativá-la, aguardar um tempo de estabilização configurável (padrão de cerca de 1 ms), ler **todas** as linhas e só então devolvê-la à entrada. Uma linha lida em HIGH enquanto a coluna `Cn` está ativa SHALL significar que o switch na coordenada `CnLm` está fechado.

#### Scenario: Tecla fechada lida na coordenada certa
- **WHEN** o switch `SW21` (`C3L3`, keycap `1`) está fechado e o scanner ativa a coluna `C3`
- **THEN** a linha `L3` (GPIO17) é lida em HIGH e a coordenada `C3L3` é reportada como fechada

#### Scenario: Leitura só com coluna ativa
- **WHEN** o scanner lê as linhas
- **THEN** exatamente uma coluna está em HIGH naquele instante

### Requirement: Debounce e eventos de pressionamento e soltura

O sistema SHALL aplicar debounce temporal configurável (padrão de cerca de 20 ms): uma mudança de estado de um switch SHALL ser emitida apenas depois de o novo estado permanecer estável por pelo menos esse intervalo (RF-11). O sistema SHALL emitir um evento ao **pressionar** e outro ao **soltar**, e cada evento SHALL conter no mínimo o keycap, a coordenada `C#L#`, o switch `SW#`, o estado (pressionado ou solto), o GPIO da coluna e o GPIO da linha.

#### Scenario: Pressionamento estável gera um único evento
- **WHEN** um switch fecha e permanece fechado por mais de 20 ms
- **THEN** é emitido exatamente um evento "pressionado" com keycap, `C#L#`, `SW#`, GPIO da coluna e GPIO da linha

#### Scenario: Ressalto é filtrado
- **WHEN** um switch alterna entre aberto e fechado várias vezes dentro de 20 ms e depois estabiliza fechado
- **THEN** é emitido um único evento "pressionado"

#### Scenario: Soltura
- **WHEN** um switch que estava pressionado abre e permanece aberto por mais de 20 ms
- **THEN** é emitido exatamente um evento "solto" para o mesmo switch

#### Scenario: Teclas simultâneas
- **WHEN** dois switches em colunas e linhas diferentes estão fechados ao mesmo tempo
- **THEN** cada um gera o seu próprio evento "pressionado", sem teclas fantasma, graças aos diodos em série

### Requirement: Posse única e liberação segura das GPIOs

O sistema SHALL requisitar as 13 GPIOs da matriz uma única vez por processo, no `gpiochip0`, com um nome de consumidor identificável. Ao encerrar, seja por saída normal, exceção, `Ctrl+C` (`SIGINT`), `SIGTERM` ou `SIGHUP`, o sistema SHALL reconfigurar todas as 13 GPIOs como entrada sem bias e só então liberar a requisição.

Antes de requisitar, o sistema SHALL confirmar que o `gpiochip0` é o controlador de GPIO do Raspberry Pi 4 e que nenhuma das 13 linhas está em uso por outro consumidor. Caso contrário, SHALL recusar a abertura com uma mensagem que nomeie o chip ou a linha em conflito.

#### Scenario: Encerramento por Ctrl+C durante a varredura
- **WHEN** o processo recebe `Ctrl+C` enquanto uma coluna está em HIGH
- **THEN** a coluna volta à entrada, todas as 13 GPIOs ficam em entrada sem bias, e a requisição é liberada

#### Scenario: Encerramento pela sessão gráfica
- **WHEN** o processo recebe `SIGTERM` ou `SIGHUP`
- **THEN** o mesmo procedimento de restauração e liberação é executado antes de o processo terminar

#### Scenario: Troca de front não libera as GPIOs
- **WHEN** o front muda de LCD para HDMI, ou o inverso (RF-09)
- **THEN** a mesma requisição de GPIO continua em uso pelo novo front, sem liberar e requisitar de novo

#### Scenario: Linha ocupada por outro consumidor
- **WHEN** uma das 13 linhas já está requisitada por outro processo ou driver
- **THEN** a abertura falha com uma mensagem que nomeia a linha e o consumidor, e nenhuma linha é reconfigurada

#### Scenario: Chip que não é o do Pi 4
- **WHEN** o `gpiochip0` não é o controlador de GPIO do BCM2711
- **THEN** a abertura é recusada, em vez de supor que offset é igual a BCM

### Requirement: Entrega das teclas aos fronts visuais

Cada pressionamento SHALL ser entregue ao front visual ativo (LCD ou HDMI) **no laço de eventos do Tk**, nunca a partir da thread de varredura, e SHALL percorrer o mesmo tratamento de tokens do teclado de PC: modificadores `Ctrl`/`Shift`, histórico, blackout e anúncios por voz. O keycap SHALL ser resolvido para a entrada completa do catálogo de teclas (função primária, função com `Ctrl` e função com `Shift`), para que as funções secundárias funcionem pela matriz. Eventos de soltura SHALL NOT gerar tokens.

A tecla `?` (`SW25`, `C0L4`) SHALL ser reconhecida e entregue, mas SHALL NOT inserir nada na expressão. O front SHALL anunciar por voz que a tecla não tem função.

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

#### Scenario: Tecla sem função
- **WHEN** o utilizador pressiona a tecla `?` da matriz
- **THEN** a expressão permanece inalterada e o front anuncia que a tecla não tem função

#### Scenario: Aplicação sem matriz disponível
- **WHEN** a aplicação arranca num PC, sem `gpiod` instalado ou sem `gpiochip0`
- **THEN** o front abre normalmente com o teclado de PC, e o log registra que a matriz não está ativa
