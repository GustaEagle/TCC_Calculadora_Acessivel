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
