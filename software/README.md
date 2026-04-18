# Software (calculadora)

Alinhado ao [PRD.md](../PRD.md) §8: **motor em Python**, **dois fronts** (LCD e HDMI), **áudio** em paralelo, módulos **sem** acoplar o núcleo à UI.

| Pasta | Conteúdo esperado |
| ----- | ------------------ |
| `core/` | Parser, precedência, funções §5, códigos de erro; API estável para as UIs. |
| `ui_lcd/` | Interface para o painel 4,3" (restrições de tamanho e legibilidade). |
| `ui_hdmi/` | Interface para monitor externo (layout mais rico). |
| `accessibility/` | TTS, fila de anúncios, política de interrupção (RF-08); idioma pt-BR. |
| `platform/` | GPIO / matriz teclado, leitura UPS quando existir, detecção de saídas HDMI (helpers). |
| `tests/` | Testes de integração ou smoke que cruzam módulos. |

Cada subprojeto pode ter o seu próprio `tests/` ou `pyproject.toml` quando a stack estabilizar.
