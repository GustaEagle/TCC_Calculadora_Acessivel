## Purpose

Definir o **motor de síntese de voz** da calculadora: um TTS neural offline em português do Brasil (Piper, voz `cadu`), residente em memória, que reproduz pela placa de áudio padrão do sistema e preserva a política de fila e interrupção já exigida pelo RF-08. Serve à inteligibilidade do PRD §8 e ao funcionamento offline do RNF-02, sem alterar o texto falado nem os consumidores do serviço de voz.

## ADDED Requirements

### Requirement: Motor de voz neural offline em pt-BR (Piper + cadu)

O sistema SHALL sintetizar a voz com o motor **Piper** (`piper-tts`, sobre `onnxruntime`), usando a voz **`pt_BR-cadu-medium`**, de forma **offline** — sem qualquer dependência de rede ou nuvem. O modelo de voz (`.onnx`) e a sua configuração (`.onnx.json`) SHALL estar embutidos na imagem e SHALL NOT ser baixados em tempo de execução.

#### Scenario: Síntese sem rede
- **WHEN** o dispositivo está sem conexão de rede e uma entrada ou resultado precisa ser anunciado
- **THEN** o texto é falado em português do Brasil pela voz `cadu`, usando o modelo local, sem acessar a rede

#### Scenario: Voz cadu carregada da imagem
- **WHEN** o serviço de voz inicializa
- **THEN** o modelo `pt_BR-cadu-medium` é carregado de um caminho local da imagem, com o `sample_rate` lido do seu `.onnx.json`

### Requirement: Motor residente, sem recarregar por frase

O modelo de voz SHALL ser carregado **uma única vez** por execução e permanecer residente em memória. O sistema SHALL NOT recarregar o modelo a cada anúncio. Cada anúncio SHALL reutilizar o motor já carregado.

#### Scenario: Modelo carregado uma vez
- **WHEN** vários anúncios são feitos em sequência
- **THEN** o modelo de voz é carregado apenas na primeira vez e reutilizado nos anúncios seguintes, sem nova carga do arquivo `.onnx`

### Requirement: Carga não-bloqueante no arranque

A carga do modelo de voz SHALL NOT bloquear o arranque da aplicação (RNF-06). Enquanto o modelo ainda não está pronto, o sistema SHALL permitir que anúncios ocorram por um caminho degradado, sem travar a interface nem a entrada.

#### Scenario: Anúncio de prontidão não espera o modelo
- **WHEN** a aplicação inicia e anuncia que está pronta, antes de o modelo neural terminar de carregar
- **THEN** o anúncio é reproduzido de imediato pelo caminho de fallback, sem aguardar a carga do modelo

### Requirement: Reprodução pela placa de áudio padrão do sistema

O áudio sintetizado SHALL ser reproduzido pela placa de áudio **padrão do ALSA** (que a imagem fixa no jack de 3,5 mm), por meio do reprodutor do sistema (`aplay`), sem depender de servidor de som (PulseAudio). Em nenhum momento SHALL haver mais de um reprodutor de áudio ativo ao mesmo tempo.

#### Scenario: Som sai pela saída padrão
- **WHEN** um anúncio é reproduzido
- **THEN** o áudio sai pela placa padrão definida na configuração do ALSA da imagem, sem PulseAudio

#### Scenario: Reprodução serializada
- **WHEN** um anúncio está tocando e outro é solicitado
- **THEN** os anúncios são reproduzidos um de cada vez, sem dois reprodutores concorrentes sobre a mesma placa

### Requirement: Preservação da fila e da interrupção (RF-08)

O motor SHALL preservar o contrato de fila e interrupção existente: um anúncio de maior prioridade (resultado ou erro P1) SHALL interromper de forma consistente o anúncio em curso ou enfileirado de menor prioridade, e apenas o anúncio mais recente MUST ser reproduzido. A entrada por teclado SHALL NOT ficar bloqueada enquanto a voz fala.

#### Scenario: Resultado interrompe anúncio de tecla
- **WHEN** uma tecla está sendo anunciada e o usuário aciona a avaliação
- **THEN** o anúncio da tecla em reprodução é cortado e o resultado é falado, sem sobrepor os dois

#### Scenario: Anúncio obsoleto descartado sem tocar
- **WHEN** uma interrupção chega enquanto uma frase de menor prioridade ainda está sendo sintetizada e ainda não começou a tocar
- **THEN** essa frase é descartada por obsolescência e não chega a ser reproduzida

#### Scenario: Entrada não bloqueia durante a fala
- **WHEN** o usuário pressiona teclas enquanto um anúncio está em curso
- **THEN** as teclas são aceitas e processadas sem esperar o fim da fala

### Requirement: Cache de frases de conjunto fechado

O sistema SHALL manter em memória o áudio pré-sintetizado das frases de **conjunto fechado** — nomes de tecla, dígitos, mensagens de erro e aviso do PRD §13 e anúncios fixos — e reproduzi-las a partir desse cache, para manter a latência por tecla baixa. Resultados e expressões dinâmicas SHALL ser sintetizados sob demanda.

#### Scenario: Nome de tecla reproduzido do cache
- **WHEN** uma tecla cujo nome falado pertence ao conjunto fixo é anunciada, após o cache estar aquecido
- **THEN** o áudio correspondente é reproduzido do cache, sem nova síntese

#### Scenario: Resultado dinâmico é sintetizado
- **WHEN** um resultado numérico precisa ser anunciado
- **THEN** ele é sintetizado sob demanda pelo motor, pois não pertence ao conjunto fixo

### Requirement: Fallback quando o motor neural está indisponível

Se o motor Piper não puder ser carregado (dependência ausente, modelo ausente ou falha de carga) ou enquanto ainda está carregando, o sistema SHALL degradar para o motor `espeak-ng`, SHALL registrar o aviso `WRN-011` (motor TTS degradado) e SHALL NOT bloquear a entrada do usuário.

#### Scenario: Piper ausente cai para espeak-ng
- **WHEN** o motor Piper não está disponível no arranque
- **THEN** os anúncios são reproduzidos por `espeak-ng`, o sistema registra `WRN-011` e a calculadora continua utilizável

#### Scenario: Falha de voz não trava a entrada
- **WHEN** ocorre uma falha pontual na síntese ou na reprodução
- **THEN** a entrada por teclado continua sendo aceita e o erro é registrado, sem interromper o uso (RF-08)

### Requirement: Contrato de integração inalterado para os consumidores

A interface pública do serviço de voz (`say`, `interrupt_and_say`, `stop`) SHALL permanecer inalterada, de modo que os fronts (LCD, HDMI e somente áudio) e o observador de vídeo continuem funcionando **sem alteração**. A troca de motor SHALL NOT exigir mudanças fora do módulo de acessibilidade.

#### Scenario: Fronts não mudam
- **WHEN** um front chama `say` ou `interrupt_and_say` como faz hoje
- **THEN** o anúncio ocorre com o novo motor, sem que o código do front precise ser alterado
