# Sistema (SO / arranque / imagem)

Área para tudo o que não é “aplicação Python” mas é necessário ao produto no Raspberry Pi 4B, conforme [PRD.md](../PRD.md) §12.

| Subpasta | Uso sugerido |
| -------- | ------------- |
| `rpi-os/` | Scripts de configuração, snippets de `config.txt`, unidades `systemd`, políticas de utilizador `kiosk`, notas de pacotes. |
| `buildroot/` | Receitas ou `defconfig` se optarem por imagem Buildroot (pode ficar vazia até haver decisão). |

**Regra:** não commitar imagens `.img` completas (ocupam muito espaço); documentar como gerar a imagem a partir de scripts ou CI, se mais tarde existir.
