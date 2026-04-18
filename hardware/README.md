# Hardware

## PCI (KiCad)

- **Canónico (recomendado):** [`pcb/`](pcb/) — um projeto KiCad por linha (ficheiros `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, bibliotecas locais em subpasta se necessário).
- **Legado / atual:** pasta **`Placa Kicad/`** na raiz do repositório — trabalho em curso; o histórico interno do KiCad (`.history/`) fica **fora do Git** (ver `.gitignore`).

Para marcos de revisão ou fabrico, use **`pcb/snapshots/<data>-<rótulo>/`** com Gerbers, PDF do esquemático, etc., em vez de versionar centenas de ficheiros de backup.

## Outros

- Layout de teclado (KLE): [`docs/keyboard-layout/`](../docs/keyboard-layout/).
- CAD mecânico: [`docs/cad/`](../docs/cad/).

Mapa geral: [docs/REPO_STRUCTURE.md](../docs/REPO_STRUCTURE.md).
