## ADDED Requirements

### Requirement: O início da fala não é cortado

O áudio de toda frase SHALL começar por um intervalo curto de **silêncio**, antes do primeiro fonema, para o dispositivo de saída acordar sem cortar o início da fala. Saídas HDMI costumam descartar os primeiros milissegundos de um fluxo, o que transformava «limpar tudo» em «impa tudo» (T01). A duração SHALL ser uma constante nomeada, ajustada pela medição no aparelho, e SHALL valer para frases sintetizadas na hora, frases do cache e o fallback `espeak-ng`.

O silêncio SHALL NOT alterar o conteúdo falado nem o comportamento da interrupção (RF-08).

#### Scenario: Frase sintetizada começa por silêncio

- **WHEN** uma frase é sintetizada e entregue para reprodução
- **THEN** o PCM entregue ao `aplay` começa pelo número de amostras nulas correspondente à duração configurada, seguido do áudio sintetizado sem alteração

#### Scenario: Frase do cache também começa por silêncio

- **WHEN** uma frase de conjunto fechado é tocada a partir do cache
- **THEN** o PCM entregue ao `aplay` começa pelo mesmo silêncio

#### Scenario: Silêncio não se acumula

- **WHEN** uma frase é tocada em vários pedaços
- **THEN** o silêncio inicial aparece **uma** vez, no início da frase, e não entre os pedaços

### Requirement: A fala de um resultado começa antes de a síntese terminar

A reprodução de uma frase SHALL começar assim que o **primeiro** pedaço de áudio estiver pronto, sem esperar a síntese da frase inteira (T04). A frase SHALL ser tocada num único processo de reprodução, alimentado em ordem com os pedaços conforme ficam prontos, para não reabrir o dispositivo a cada pedaço.

Um pedaço que exista no cache de conjunto fechado (o prefixo «Resultado», os rótulos dos pares, os dígitos de 0 a 9, «vírgula», «menos») SHALL sair do cache, sem síntese. Só o que não estiver no cache é sintetizado, como as partes inteiras lidas como cardinal.

Um novo toque SHALL interromper a frase inteira, incluindo os pedaços ainda não sintetizados ou não tocados (RF-08).

#### Scenario: Prefixo toca antes de o número estar pronto

- **WHEN** a frase `"Resultado 53 vírgula 1 3"` é falada com um motor de síntese lento
- **THEN** o áudio de «Resultado» começa a ser entregue ao processo de reprodução antes de a síntese de «53» terminar

#### Scenario: Pedaços tocados na ordem da frase

- **WHEN** uma frase é tocada em pedaços
- **THEN** o áudio entregue ao processo de reprodução segue a ordem das palavras da frase, independentemente da ordem em que os pedaços ficam prontos

#### Scenario: Dígitos da parte fracionária saem do cache

- **WHEN** a frase `"Resultado 1 vírgula 7 3 2"` é falada com o cache aquecido
- **THEN** só «1» pode ser sintetizado na hora: «Resultado», «vírgula», «7», «3» e «2» vêm do cache

#### Scenario: Interrupção descarta os pedaços pendentes

- **WHEN** uma frase está a meio da reprodução e uma nova tecla é pressionada
- **THEN** o processo de reprodução é terminado, os pedaços ainda não tocados são descartados e a nova fala começa

#### Scenario: Um só processo de reprodução por frase

- **WHEN** uma frase de vários pedaços é tocada
- **THEN** é aberto exatamente um processo `aplay` para a frase inteira
