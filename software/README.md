# Software (calculadora)

Alinhado ao [PRD.md](../PRD.md) §8: **motor em Python**, **dois fronts** (LCD e HDMI), **áudio** em paralelo, módulos **sem** acoplar o núcleo à UI.

| Pasta | Conteúdo esperado |
| ----- | ------------------ |
| `core/` | Parser, precedência, funções §5, códigos de erro; API estável para as UIs. |
| `app.py` | Ponto de entrada: escolhe a saída ativa (§7) e inicia **um** front. |
| `ui/lcd/` | Interface para o painel 4,3" (restrições de tamanho e legibilidade). |
| `ui/hdmi/` | Interface para monitor externo (layout mais rico, responsivo à resolução). |
| `ui/shared/` | O que os dois fronts partilham: textos de erro §13, paleta, teclado, formatação, escala. |
| `audio_only.py` | Modo somente áudio (RF-04), sem janela gráfica. |
| `accessibility/` | TTS, fila de anúncios, política de interrupção (RF-08); idioma pt-BR. |
| `hw_platform/` | GPIO / matriz teclado, leitura UPS quando existir, detecção de saídas HDMI (helpers). |
| `tests/` | Testes de integração ou smoke que cruzam módulos. |

Cada subprojeto pode ter o seu próprio `tests/` ou `pyproject.toml` quando a stack estabilizar.

## Dependências

- **Python:** `ttkbootstrap` e `pyttsx3`, com versões fixadas em [requirements.txt](requirements.txt) (`ttkbootstrap==1.20.4`, `pyttsx3==2.99`).
- **Sistema:** `python3-tk` (Tkinter) e **`espeak-ng`** para o TTS.
  > ⚠️ Use **`espeak-ng`**, **não** o `espeak` clássico: este último é incompatível com o driver do `pyttsx3` (falha com `SetVoiceByName ... gmw/en`) e o áudio não inicia. Vale para qualquer forma de empacotar (Docker, Pi OS, Buildroot).
- **Testes:** só a biblioteca padrão (`unittest`) — nenhuma dependência extra. Ver `make check`.
