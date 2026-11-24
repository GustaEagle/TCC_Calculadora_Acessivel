# UPS HAT (Waveshare) — notas para o repositório

**Fonte:** [Waveshare Wiki — UPS HAT](https://www.waveshare.com/wiki/UPS_HAT)  
**Página do produto:** [UPS-HAT.htm](https://www.waveshare.com/UPS-HAT.htm)  
**Snapshot local:** 2026-04-17

UPS HAT para Raspberry Pi: alimentação ininterrupta a **5 V**, circuitos de proteção de bateria e comunicação por **I2C** para monitorização de tensão, corrente, potência e capacidade restante.

---

## Características (resumo)

- Header GPIO de **40 pinos** padrão Raspberry Pi.
- Barramento **I2C** para leitura em tempo real (tensão, corrente, potência, capacidade restante).
- Proteções: sobrecarga / sobredescarga, sobrecorrente, curto‑circuito, polaridade inversa; carga equilibrada entre células.
- Regulador **5 V** onboard, até **2,5 A** contínuos (valor indicado na wiki).
- Saída **5 V USB** para alimentar outros módulos.
- LEDs de **aviso** das baterias (útil para detetar inversão de polaridade na instalação).

---

## Especificações indicadas na wiki

| Parâmetro | Valor |
| --------- | ----- |
| Tensão de saída | 5 V |
| Carregador | **8,4 V, 2 A** |
| Barramento de controlo | I2C |
| Bateria | 18650 Li **3,7 V** (não incluídas) |
| Capacidade de referência no material demo | **5200 mAh** total para 2 células (exemplo; baterias não incluídas) |
| Dimensões | 56 mm × 85 mm |
| Furo de montagem | 3,0 mm |

---

## Hardware e segurança

- A interface **8,4 V** é a **porta de carregamento**; usar o carregador adequado (8,4 V / 2 A) indicado pelo fabricante.
- O **interruptor** liga/desliga a alimentação (na documentação Waveshare também referem uso com Jetson Nano).
- **LEDs WARNING:** acendem se as baterias estiverem **invertidas**. **Não carregar** com polaridade invertida.
- Na **primeira instalação** das baterias, a placa pode não arrancar de imediato; pode ser necessário **carregar um pouco** para “ativar” as células.
- Usar **carregador adequado**; adaptadores inadequados podem danificar o módulo.

### Avisos de segurança (Li‑ion / Li‑po)

- Risco de incêndio ou danos se recarga ou uso forem incorretos.
- Não inverter polaridade; não usar carregadores de má qualidade.
- Não misturar baterias velhas com novas nem marcas diferentes.
- Comprar baterias compatíveis e de fabricantes fiáveis; respeitar ciclos de vida e substituir quando apropriado (a wiki sugere substituição após vida útil de ciclos ou **mais de dois anos**, o que ocorrer primeiro).
- Armazenar longe de inflamáveis e de crianças.

---

## Raspberry Pi: ativar I2C

```bash
sudo raspi-config
```

Interfacing Options → I2C → **Yes**, depois reiniciar:

```bash
sudo reboot
```

A HAT pode ir empilhada nos **40 pinos** ou ligada por fios; na ligação manual, **VCC** ao **3,3 V** conforme indicação da wiki (confirmar no esquemático do seu lote).

---

## Demo e código de exemplo (wiki)

```bash
sudo apt-get install p7zip
wget https://files.waveshare.com/upload/d/d9/UPS_HAT.7z
7zr x UPS_HAT.7z -r -o./UPS_HAT
cd UPS_HAT
python3 INA219.py
```

Após iniciar o servidor de exemplo, o terminal pode mostrar IP, tensão da bateria, corrente, percentagem estimada, e informação de CPU/GPU/memória (conforme demo).

**Sinal da corrente:**

- **Corrente negativa:** as baterias estão a **alimentar** o Raspberry Pi.
- **Corrente positiva:** as baterias estão a **carregar**.

---

## Implementação no software

O nível da bateria é lido em `software/hw_platform/ups.py` (`UpsMonitor`):

- Lemos o registrador **Bus Voltage (0x02)** do INA219 no endereço **0x42**,
  barramento **I2C1** (`/dev/i2c-1`). Esse registrador é preenchido pelo próprio
  chip após o reset, sem precisar escrever a calibração — logo basta **ler**.
- A leitura usa o **`i2cget`** (`i2c-tools`, já na imagem), no mesmo estilo do
  resto do projeto (chama binários do sistema: `aplay`, `xrandr`, `amixer`), sem
  acrescentar uma biblioteca Python de I2C. O `i2cget ... w` devolve a palavra
  em little-endian; o INA219 é big-endian, então os bytes são trocados.
- Tensão = `(raw >> 3) * 4 mV`; percentagem = `(V − vazio) / (cheio − vazio)`,
  com `vazio = 3,0 V` e `cheio = 4,2 V` (duas células em paralelo). Endereço,
  barramento e tensões de referência são ajustáveis por ambiente
  (`CALC_UPS_I2C_BUS`, `CALC_UPS_I2C_ADDR`, `CALC_UPS_EMPTY_V`, `CALC_UPS_FULL_V`).
- Sem I2C/`i2cget` (fora do Pi) a leitura **não é inventada**: o status volta com
  `available=False` e o monitor de bateria simplesmente não alerta.

### Aviso de bateria (WRN-020)

O aviso fica em `software/accessibility/battery_alert.py` (`BatteryMonitor`), e
tem **dois níveis**, ambos com o código **WRN-020** do PRD §13 (no log e no
catálogo; a voz não diz o número do aviso):

| Nível | Limite | Som | Voz | Tela |
| --- | --- | --- | --- | --- |
| Bateria baixa | **20 %** (`CALC_UPS_LOW_PERCENT`) | 2 bipes | «Bateria baixa, 18 por cento. Conecte o carregador.» | `BATERIA BAIXA 18%` em laranja |
| Bateria no fim | **10 %** (`CALC_UPS_CRITICAL_PERCENT`) | 3 bipes, mais agudos e rápidos | «Bateria no fim, 7 por cento. A calculadora vai desligar. Conecte o carregador agora.» | `BATERIA NO FIM 7%` em vermelho |

- Os bipes e a frase são **uma** mensagem, com prioridade crítica: cortam e
  precedem qualquer outro áudio, e nada os corta, a não ser outro alerta.
- O indicador aparece à direita da barra de indicadores, nos dois fronts, e
  fica **vazio** com a bateria normal ou sem UPS.
- Anti-repetição:
  - repete se a carga cair mais **5 pontos** (`CALC_UPS_RENOTIFY_DROP`);
  - repete se passarem **5 min** no nível baixo (`CALC_UPS_RENOTIFY_INTERVAL_S`)
    ou **1 min** no nível no fim (`CALC_UPS_CRITICAL_RENOTIFY_INTERVAL_S`);
  - avisa **na hora** ao passar de baixa para no fim;
  - rearma quando a carga volta a subir com folga (3 pontos acima do limite).
- Leitura a cada **30 s** (`CALC_UPS_POLL_INTERVAL_S`).

**Requisito na imagem do Pi:** o módulo `i2c-dev` tem de ser carregado no
arranque. No kernel `linux-rpi` ele é **módulo**, e o `dtparam=i2c_arm=on` só
liga o controlador: sem `i2c-dev` o `/dev/i2c-1` nunca aparece, e o monitor
conclui que não há UPS, sem avisar. O `build-alpine-img.sh` acrescenta
`i2c-dev` ao `/etc/modules` (em `apply_overlay_and_app`, que corre também com
`CONTINUE=1`).

### Testar o aviso

**No PC** (sem UPS), com bateria simulada que desce 1 ponto a cada 2 s:

```
python -m software.app --force-mode lcd --simulate-battery 15 --keypad-matrix off
```

Em 2 s aparece o aviso de bateria baixa, e em cerca de 12 s o de bateria no fim.
A variável `CALC_SIMULATE_BATTERY=15` faz o mesmo que a opção.

**No Pi**, com o UPS de verdade:

1. `ls /dev/i2c-1` e `i2cdetect -y 1`: o barramento existe e o chip responde em `42`.
2. Leitura que a calculadora faz:
   `python3 -c "from software.hw_platform.ups import UpsMonitor; print(UpsMonitor().read_status())"`
   (a partir de `/opt/calculadora`).
3. Para ouvir e ver o aviso sem esperar a bateria descarregar, suba o limite
   acima da carga atual: `CALC_UPS_LOW_PERCENT=101 CALC_UPS_POLL_INTERVAL_S=5`
   antes de iniciar a calculadora. O aviso sai da leitura **real** do I2C.
4. Para testar só o som e a tela, a simulação também funciona no Pi
   (`--simulate-battery 15`).

## Endereço I2C

Na FAQ da wiki, o endereço indicado é **0x42**. Para verificar no sistema:

```bash
sudo apt-get install i2c-tools
sudo i2cdetect -y 1
```

(Em alguns modelos de Pi o barramento pode ser `0` em vez de `1`; ajuste conforme a sua placa.)

---

## Recursos para download (oficiais)

- [Demo codes — UPS_HAT.7z](https://files.waveshare.com/upload/d/d9/UPS_HAT.7z)
- [Demo codes V2 — UPS_HAT_V2.zip](https://files.waveshare.com/wiki/UPS_HAT_B/UPS_HAT_V2.zip)

Cópia local do STEP da HAT: pasta [`../cad/waveshare-ups-hat/`](../cad/waveshare-ups-hat/) (ver [`../cad/README.md`](../cad/README.md)).

Na wiki, na secção **Document**, há ainda ligações para desenho 3D, esquemático e datasheets (INA219, HY2120, HY2213). **Consulte sempre a página atual** para URLs atualizadas.

---

## FAQ (resumo da wiki)

| Questão | Resposta resumida |
| ------- | ----------------- |
| Altura com o Pi | ~**42,05 mm** empilhado. |
| Indicador do carregador | **Vermelho** a carregar; **verde** carregado (com carga ligada o estado pode manter‑se em vermelho — ver FAQ “green to red”). |
| Corrente negativa | Baterias a alimentar o Pi. |
| Tempo de carga (indicativo) | Da ordem de **~3 h** (condições dependentes das células e carga). |
| Desligar com bateria baixa | Por I2C é possível ler tensão/corrente/capacidade e **programar** gravação de dados e **shutdown** ordenado. |
| Percentagem ~88% “cheio” | O demo assume **5200 mAh**; com outras capacidades é preciso **ajustar parâmetros** no programa. |
| Duas fontes vs uma | Usar **apenas** a fonte **8,4 V / 2 A** na HAT é suficiente para o Pi na orientação da wiki; **não** ligar fonte direta ao Pi em paralelo conforme essa recomendação. |
| Arranque após instalar baterias | Pode ser preciso **carregar primeiro** para iniciar; se persistir falha, a wiki indica medições de tensão (ver **figuras na página oficial**). |

Para perguntas com **diagramas** (USB externo, teste de tensão, etc.), abra a [página oficial](https://www.waveshare.com/wiki/UPS_HAT).
