# Materiais e Métodos (TCC)

Esta lista detalha os componentes de hardware e materiais utilizados na construção do protótipo da Calculadora Científica Acessível, documentando suas especificações e finalidades dentro do escopo do projeto de Trabalho de Conclusão de Curso (TCC).

## 1. Placa de Processamento Principal

### Raspberry Pi 4 Model B
* **Especificações Principais:** 8GB de RAM.
* **Descrição:** A unidade principal de processamento (Single-Board Computer) para o projeto. É responsável por rodar o Sistema Operacional e o motor de cálculo da aplicação integrado à lógica visual (via saídas HDMI para monitor e LCD) e sonora (TTS pelo áudio) do projeto de acessibilidade.

## 2. Periféricos de Tela e Interface

### 4.3inch HDMI LCD (B)
* **Produto:** 4.3inch Capacitive Touch Screen LCD
* **Especificações:**
  * Tecnologia TFT IPS com tela de 4.3 polegadas.
  * Resolução em hardware de 800 × 480 pixels.
  * Controle por toque capacitivo de 5 pontos; painel de vidro temperado de dureza até 6H.
  * Possui *Jack de áudio* embutido de 3.5mm para alto-falante, extraindo suporte nativo de áudio via HDMI.
  * Menu OSD multicamada controlado por botões para gerenciar energia, brilho e contraste.
* **Descrição:** Funciona como o painel local do produto. Comportando-se como interface principal caso o monitor externo não esteja presente. Pode ter sua visualização suspensa através do envio de sinais controlados ou pelo interruptor de energia do vídeo. É montado externamente e suporta os sistemas operacionais principais do projeto.
* **Link de Referência:** [Wiki Waveshare 4.3inch HDMI LCD (B)](https://www.waveshare.com/wiki/4.3inch_HDMI_LCD_(B))

### Cabo Plano Flexível (FFC) compatível com HDMI
* **Nome do Produto:** Cabo plano flexível compatível com HDMI FFC, Raspberry Pi 4 Micro H, DMI para HD, Mini HDM I, 90 graus, FFC, Fita de 20Pin FPV
* **Variantes Adquiridas:** Conectores A4, D1, e fita FFC medindo 15cm.
* **Descrição:** Um cabo em formato achatado de 20-pinos focado em espaços curtos/aero (FPV) e com angulação a 90°. Projetado para estabelecer um canal direto que transmita os dados da conexão Micro HDMI (A4) provinda do Pi 4 para as conexões Mini HDMI ou Standard (D1) da tela LCD, ocupando pouco volume físico na espessura do equipamento.
* **Link:** [AliExpress](https://pt.aliexpress.com/item/1005004030924780.html)

## 3. Gestão e Alimentação

### UPS HAT (Uninterruptible Power Supply)
* **Model:** UPS HAT para Raspberry Pi
* **Especificações:**
  * Opera com interface padrão de 40-Pinos do Raspberry Pi (GPIO header).
  * Comunicação de barramento I2C, monitorando ativamente tensão de baterias, corrente, energia elétrica e capacidade limite contínua.
  * Regulador a bordo de 5V gerando correntes de saída de até 2.5A.
  * Suporta duas baterias do formato de Lítio (Li) 18650 de 3.7V (oferecendo idealmente em total 5200mAh instalados).
  * Requerimento para carga total de entrada: 8.4V 2A através do plugue DC.
  * Elementos de circuitos integrados englobam proteção para: curto-circuito, sobrecarga ou descarga excessiva, reverso na polaridade da bateria e um sistema atuando balanço de recarga (equalizing charge).
  * Medições do módulo de 56mm x 85mm.
* **Descrição:** É o cérebro auxiliar de estabilidade operacional — fornecendo uma funcionalidade perene no estilo bateria de *notebook*. Ajuda na continuidade elétrica isolada e suporta verificação das correntes via I2C. Quando o poder da capacidade entra num nível abaixo, é ele quem provê o gatilho para os avisos por interface de áudio (TTS) sem impor reinicialização forçada abrupta do Pi.
* **Link de Referência:** [Wiki Waveshare UPS HAT](https://www.waveshare.com/wiki/UPS_HAT)

## 4. Teclado Mecânico Físico Tátil

### Cherry MX Red Switches
* **Produto:** Switch Red 
* **Especificações:**
  * Estilo de Chave: Linear.
  * Força de Atuação Requerida (Resistência): Leve, de apenas 45 cN.
  * Ponto de Pré-Curso: Distância curta em torno de 2.0 mm de fundo de tecla de acionamento rápido base.
  * Curso Total: 4.0 mm.
  * Resistência certificada: Mais de 100 milhões de repetições suportadas no switch.
* **Descrição:** Adotados para perfazer a rede de botões tátil principal (organizados numa matriz customizada 7x7 de portas lógicas atreladas nas interfaces GPIO). Eles asseguram digitações mais constantes e velozes para o usuário, ao mesmo tempo criando uma ausência do 'click' mecânico notório o que deixa a trilha mais suave (linearidade), e deixa a evidência puramente atrelada aos anúncios áudios (bipe eletrônico / voz) da Calculadora Acessível.
* **Link de Referência:** [Guia do Switch Cherry MX](https://www.daskeyboard.com/blog/cherry-mx-switches/)

## 5. Áudio e Retorno Auxiliar (TTS)

### Cabo de Áudio 90 Graus 3.5mm TRS
* **Nome do Produto:** 90 graus 3.5mm trs/trrs cabo de áudio estéreo 3.5mm a 3.5mm ângulo direito cabo aux para fone de ouvido mp3 smartphone tablet alto-falantes do carro
* **Especificações:** Comprimento de 0.2m (20 centímetros), 3 Polos TRS operantes na modalidade Macho para Fêmea e extremidades contornadas com geometria ergonômica de 90° (ângulo direito).
* **Descrição:** Solução física restrita para cabiar internamente a saída de áudio base do minicomputador para as aberturas do gabinete em direção aos fones de ouvidos de usuário do TCC, acomodando mais perfeitamente no compartimento sem que dobras excessivas do cabo de áudio resultem no mal contato e que a estabilidade das ondas vitais de informações verbais acustificadas fiquem resguardadas.
* **Link:** [AliExpress](https://pt.aliexpress.com/item/1005008288720867.html)

## 6. Integrantes Customizados Físicos

### Placa de Circuito Impresso (PCI)
* **Características / Dimensões:** Modelo dupla face de tamanho limite de 15×15 cm.
* **Método de Confecção:** Placa em base de tipo Fenolite. O design logístico efetuado através do KiCad com subsequente gravação corrosiva num laboratório físico utilizando percloreto de ferro.
* **Descrição:** A fundação rígida do layout âncora; que alinha eletrificamente as bases operantes dos perfis de switches do tipo *hotswap*. É um substrato desenhado explicitamente contendo em si cabeçotes do cabeamento conectivo paralelo no formato de trilha (cabo flat) que termina sendo ligado nos terminais elétricos nativos expansivos do Raspberry Pi em formato de 7x7 portas de colunas interligadas.

### Elementos Braille de Encapsulamento
* **Composição de Obra / Fabrica:** Estruturada no elemento de modelagem termoplástica chamado PLA nativo. O procedimento material é manufaturado pela impressora compacta 3D modelo *Bambu Lab A1*.
* **Descrição:** Corpos e superfícies táteis de acoplamento do controle dos chassis (botões, *switches* de interruptores das peças do LCD) contendo demarcações estendidas das texturas do formato da linguística brasileira de deficiência visual (Braille PT-BR). Propõem um ambiente onde os utilizadores do limite físico de cegueira ou visibilidade reduzida alcancem acessibilidade na indicação de operação do hardware local.
