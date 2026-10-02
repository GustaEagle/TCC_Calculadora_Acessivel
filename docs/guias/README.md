# Guias — operação e montagem

Como **usar** a calculadora e como **fazer o aparelho rodar**. Documentos de procedimento: seguem passo a passo, do começo ao fim.

| Documento | Para quem | Conteúdo |
| --------- | --------- | -------- |
| [teclado-matriz.md](teclado-matriz.md) | Quem usa o produto | **Teclado físico (matriz 6×7)**: catálogo das 38 teclas com posição `C#L#`/`SW#`, layout da grade, funções com `Ctrl`/`Shift`, leitura por GPIO e diagnóstico |
| [comandos-teclado.md](comandos-teclado.md) | Quem desenvolve e testa | **Teclado de PC**: modificadores fixos, histórico, última resposta, graus/radianos, apagar telas, modo somente áudio |
| [build-img-linux.md](build-img-linux.md) | Quem monta o aparelho | Arranque em modo **kiosk** no Raspberry Pi 4B: Pi OS Lite, Alpine ou Buildroot; prós, contras e passos de cada opção |

## Relacionado

- Qual tecla está em qual GPIO: [../raspberry-pi-4b/pinout.md §6](../raspberry-pi-4b/pinout.md)
- Legendas e geometria do teclado: [../keyboard-layout/README.md](../keyboard-layout/README.md)
- `config.txt` e cablagem dos periféricos: [../waveshare/README.md](../waveshare/README.md)
