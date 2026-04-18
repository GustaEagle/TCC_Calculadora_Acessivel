# Estrutura do repositório (mapa PRD → pastas)

Este documento liga o [PRD.md](../PRD.md) à organização de código e hardware. **Não é obrigatório** criar tudo antes do primeiro commit: pastas vazias podem ganhar ficheiros à medida que as tasks avançam; a árvore abaixo é a **direção** acordada.

---

## Resumo visual

| Área no PRD | Pasta(s) |
| ----------- | -------- |
| Motor de cálculo (§8), Python | [`software/core/`](../software/core/) |
| Front LCD 7.x (§7) | [`software/ui_lcd/`](../software/ui_lcd/) |
| Front monitor HDMI (§7) | [`software/ui_hdmi/`](../software/ui_hdmi/) |
| Áudio / TTS / acessibilidade (§8) | [`software/accessibility/`](../software/accessibility/) |
| GPIO, UPS, detecção HDMI, integração | [`software/platform/`](../software/platform/) |
| Testes (cruzados ou por módulo) | [`software/tests/`](../software/tests/) + `tests/` dentro de cada pacote quando fizer sentido |
| PCI KiCad, fenolite (§6) | [`hardware/pcb/`](../hardware/pcb/) — ver nota sobre `Placa Kicad/` |
| Imagem SO, `config.txt`, arranque, scripts (§12) | [`system/`](../system/) |
| Datasheets, CAD, pinout, Waveshare | [`docs/`](../docs/) (já existente) |
| Cronograma interativo | [`Cronograma/`](../Cronograma/) |

---

## KiCad e várias versões

- O projeto atual pode continuar em **`Placa Kicad/`** até migrarem sem problemas de caminhos; a pasta alvo versionada é **`hardware/pcb/<nome-do-projeto>/`** (um `.kicad_pro` por linha de produto).
- O KiCad gera **`/.history/`** com muitos ficheiros: está **ignorado no Git** (ver [`.gitignore`](../.gitignore)). Para marcos (revisão, envio à gráfica), use **`hardware/pcb/snapshots/`** com subpastas datadas (ex.: `2026-06-10-gerbers-review/`) contendo export explícito (Gerber, PDF esquemático, STEP se necessário).

---

## Criar pastas “já” vs ir commitando

- **Convém** ter o **esqueleto** `software/*` e `system/` desde cedo: todos sabem onde pôr ficheiros e o PRD cita modularidade (RNF-04).
- **Não é obrigatório** preencher cada pasta na primeira sprint: ficheiros aparecem com as features.
- Quem trabalha com IA: no início da sessão, o [`Prompts/bootstrap.txt`](../Prompts/bootstrap.txt) já pede leitura do PRD; **não é necessário um agente novo** só para pastas — opcionalmente mencionar *“seguir docs/REPO_STRUCTURE.md”* no chat se estiverem a refatorar árvore.

---

## Migração sugerida (quando quiserem)

1. Copiar ou mover o `.kicad_pro` + `.kicad_sch` + `.kicad_pcb` (+ bibliotecas locais) para `hardware/pcb/tcc-calculadora/` (nome ajustável).
2. Manter `Placa Kicad/` só como arquivo ou apagar após validar que o Git e o KiCad abrem o novo caminho.
3. Registar no [`docs/CONTEXT.md`](CONTEXT.md) a pasta canónica da PCB.
