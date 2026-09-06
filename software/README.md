# Software (calculadora)

Alinhado ao [PRD.md](../PRD.md) §8: **motor em Python**, **dois fronts** (LCD e HDMI), **áudio** em paralelo, módulos **sem** acoplar o núcleo à UI.

| Pasta | Conteúdo esperado |
| ----- | ------------------ |
| `core/` | Parser, precedência, funções §5, códigos de erro; API estável para as UIs. |
| `app.py` | Ponto de entrada: escolhe a saída ativa (§7) e inicia **um** front. |
| `ui/lcd/` | Painel 4,3" — **somente a tela** (800x480 fixo): sem teclado nem botões, entrada só pelo teclado físico. |
| `ui/hdmi/` | Monitor externo — janela do tamanho da tela ativa, com **composição e tipografia derivadas da resolução** (ver "Faixas de layout" abaixo). |
| `ui/shared/` | O que os dois fronts partilham: textos de erro §13, paleta, teclado, formatação, histórico, regras de layout. |
| `audio_only.py` | Modo somente áudio (RF-04), sem janela gráfica. |
| `accessibility/` | TTS, fila de anúncios, política de interrupção (RF-08); idioma pt-BR. |
| `hw_platform/` | GPIO / matriz teclado, leitura UPS quando existir, detecção de saídas HDMI (helpers). |
| `tests/` | Testes de integração ou smoke que cruzam módulos. |

## Faixas de layout (front HDMI)

O monitor externo não tem resolução conhecida, então o front escolhe **na
construção** o que cabe na tela — como a calculadora do Windows, que vai
soltando painéis conforme estreita. Teclado e histórico são conveniências: a
entrada real é o **teclado físico** (RF-05), então nenhuma faixa reduz o
catálogo de operações do PRD §5.

| Faixa | A partir de | Mostra |
| ----- | ----------- | ------ |
| completa | 1200x700 | expressão, resultado, teclado e histórico |
| média | 900x600 | expressão, resultado e teclado |
| compacta | abaixo disso | expressão e resultado |

A tipografia acompanha a resolução por um fator `min(largura/1280, altura/720)`
limitado a **[0,75 ; 2,0]** — o piso protege quem tem visão parcial (PRD §4), o
teto evita que num 4K sobrem três botões por linha.

Os limiares e a escala vivem **num ponto só**, em
[`ui/shared/layout.py`](ui/shared/layout.py): ajustar um número não exige ler o
front inteiro. O módulo é livre de Tk de propósito, e por isso testável sem
display (`tests/test_hdmi_layout_tiers.py`); a ligação com os widgets é
verificada à parte, com janela (`tests/test_hdmi_layout_wiring.py`).

A janela **não** redimensiona: a decisão é tomada uma vez. Numa troca de saída
de vídeo (RF-09) o front é reconstruído, e aí a tela nova é lida de novo.

Cada subprojeto pode ter o seu próprio `tests/` ou `pyproject.toml` quando a stack estabilizar.

## Dependências

- **Python:** `ttkbootstrap` e `pyttsx3`, com versões fixadas em [requirements.txt](requirements.txt) (`ttkbootstrap==1.20.4`, `pyttsx3==2.99`).
- **Sistema:** `python3-tk` (Tkinter) e **`espeak-ng`** para o TTS.
  > ⚠️ Use **`espeak-ng`**, **não** o `espeak` clássico: este último é incompatível com o driver do `pyttsx3` (falha com `SetVoiceByName ... gmw/en`) e o áudio não inicia. Vale para qualquer forma de empacotar (Docker, Pi OS, Buildroot).
- **Testes:** só a biblioteca padrão (`unittest`) — nenhuma dependência extra. Ver `make check`.
