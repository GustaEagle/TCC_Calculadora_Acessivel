## ADDED Requirements

### Requirement: O separador decimal é falado como "vírgula"

Um número decimal SHALL ser falado com o separador "**vírgula**", na convenção pt-BR (T02). A parte inteira SHALL ser mantida como dígitos, para o motor de voz a ler como cardinal. A parte fracionária SHALL ser lida **dígito a dígito**, para preservar zeros à esquerda e intermédios. O sinal negativo SHALL ser falado como "menos".

Um texto que não seja um número decimal ou inteiro simples (notação científica, por exemplo) SHALL ser devolvido intacto.

#### Scenario: Decimal simples

- **WHEN** o número `1.2` é falado
- **THEN** o texto entregue ao TTS é `"1 vírgula 2"`

#### Scenario: Zeros na parte fracionária

- **WHEN** o número `0.05` é falado
- **THEN** o texto entregue ao TTS é `"0 vírgula 0 5"`, sem perder os zeros

#### Scenario: Decimal negativo

- **WHEN** o número `-3.5` é falado
- **THEN** o texto entregue ao TTS é `"menos 3 vírgula 5"`

#### Scenario: Decimal sem parte inteira

- **WHEN** o número `.5` é falado
- **THEN** o texto entregue ao TTS é `"0 vírgula 5"`

#### Scenario: Inteiros não mudam

- **WHEN** os números `10` e `-7` são falados
- **THEN** os textos entregues ao TTS são `"10"` e `"menos 7"`

#### Scenario: Decimal dentro de uma expressão

- **WHEN** a expressão `3.14*2` é lida em voz alta
- **THEN** o texto entregue ao TTS é `"3 vírgula 1 4 vezes 2"`

### Requirement: O separador de argumentos é falado como "ponto e vírgula"

Com a vírgula reservada ao decimal, o separador de argumentos (`,` em `Pol(3,4)`) SHALL ser falado como "**ponto e vírgula**", e a tecla que insere o ponto decimal SHALL ser anunciada como "vírgula". Se os dois tivessem o mesmo nome, «3 vírgula 4» seria ambíguo entre o decimal 3,4 e dois argumentos.

A **tela** SHALL continuar a mostrar `.` como separador decimal: esta mudança é só do que é falado.

#### Scenario: Tecla do ponto decimal

- **WHEN** a tecla que insere `.` é pressionada
- **THEN** o anúncio é `"vírgula"`

#### Scenario: Tecla do separador de argumentos

- **WHEN** `Shift` e a tecla do ponto são pressionados, inserindo `,`
- **THEN** o anúncio é `"ponto e vírgula"`

#### Scenario: Argumentos de uma conversão

- **WHEN** a expressão `polar(3,4)` é lida em voz alta
- **THEN** o texto contém `"3 ponto e vírgula 4"`, e não `"3 vírgula 4"`

#### Scenario: Decimal e separador na mesma expressão

- **WHEN** a expressão `polar(1.5,2)` é lida em voz alta
- **THEN** o texto contém `"1 vírgula 5 ponto e vírgula 2"`

### Requirement: Funções com parênteses anunciam a abertura

O nome falado de toda função cujo token abre parênteses (`sqrt(`, `sen(`, `log(`, `polar(`, `exp(` e as demais) SHALL terminar com «, **abre parênteses**» (T03). Assim quem ouve sabe que começou um grupo, que depois é fechado por «fecha parênteses». O mesmo nome SHALL ser usado no retorno da tecla e na leitura da expressão (`Shift` + `Ans`), para as duas não divergirem.

#### Scenario: Retorno da tecla de função

- **WHEN** a tecla `√` é pressionada
- **THEN** o anúncio é `"raiz quadrada, abre parênteses"`

#### Scenario: Leitura de uma expressão com função

- **WHEN** a expressão `sqrt(9)` é lida em voz alta
- **THEN** o texto é `"raiz quadrada, abre parênteses 9 fecha parênteses"`

#### Scenario: Todas as funções com parênteses

- **WHEN** o nome falado de cada token do catálogo que termina em `(` é consultado
- **THEN** todos terminam com `", abre parênteses"`, e nenhum token sem parênteses (como `+`, `π` ou ` nCr `) o tem

#### Scenario: Parêntese simples não duplica

- **WHEN** a tecla `(` é pressionada
- **THEN** o anúncio é `"abre parênteses"`, sem repetição

### Requirement: Dicionário de pronúncia separado do rótulo

SHALL existir um único lugar, em `ui/shared/keypad.py`, onde o **texto entregue ao motor de voz** de uma tecla pode diferir do seu nome no catálogo, para corrigir palavras que a voz pronuncie mal (T01). O rótulo exibido na tela SHALL NOT mudar por causa dele. Toda entrada do dicionário SHALL ter motivo registrado (a palavra e como soava) e SHALL ter sido confirmada numa escuta no aparelho.

#### Scenario: Correção de pronúncia não muda a tela

- **WHEN** uma tecla tem uma entrada no dicionário de pronúncia
- **THEN** o texto entregue ao TTS é o do dicionário, e o rótulo do botão e o símbolo exibido na expressão permanecem os de sempre

#### Scenario: Teclas sem correção

- **WHEN** uma tecla não tem entrada no dicionário de pronúncia
- **THEN** o texto entregue ao TTS é o nome do catálogo, sem alteração

### Requirement: Mesma leitura de resultado em todos os modos

O texto falado de um resultado SHALL ser produzido por uma **única** função partilhada pelo front do LCD, pelo front do monitor externo e pelo modo somente áudio. Um par é lido pela leitura de pares, e um escalar pela leitura de números (RF-04, RF-10).

#### Scenario: Escalar igual nos três modos

- **WHEN** `1.2+0` é avaliado no LCD, no monitor externo e no modo somente áudio
- **THEN** os três anunciam `"Resultado 1 vírgula 2"`

#### Scenario: Par no modo somente áudio

- **WHEN** `polar(3,4)` é avaliado no modo somente áudio
- **THEN** o anúncio usa a leitura de par polar, e SHALL NOT conter `(`, `)` ou `,` da tupla
