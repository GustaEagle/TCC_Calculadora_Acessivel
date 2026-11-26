# Layout de teclado (Keyboard Layout Editor)

Este diretório contém dois ficheiros:

| Ficheiro | O que é |
| -------- | ------- |
| [mapa-teclado.html](mapa-teclado.html) | **Mapa interativo das 38 teclas** — abre por duplo-clique no navegador. Grade 6×7 com seletor de camada (sozinha / `Ctrl` / `Shift`), clique numa tecla para ver `SW#`, coordenada `C#L#`, as três funções e o nome que a **voz** anuncia. Destaca os keycaps que precisam de ser trocados de posição no hotswap. |
| [keyboard-layout(9).json](keyboard-layout%289%29.json) | Layout **visual** no formato do [Keyboard Layout Editor](https://www.keyboard-layout-editor.com/) (KLE), para desenhar/imprimir a disposição física. |

> O `mapa-teclado.html` é **gerado** a partir de
> [`keypad_pinout.py`](../../software/hw_platform/keypad_pinout.py) (posições e keycaps) e
> [`keypad.py`](../../software/ui/shared/keypad.py) (funções e nomes falados). Se o código
> mudar, regere-o em vez de o editar à mão — os dados estão no array `KEYS` no fim do
> ficheiro. A referência em texto das mesmas funções é
> [`docs/guias/teclado-matriz.md`](../guias/teclado-matriz.md).

---

## Sobre o ficheiro KLE

### Como abrir ou editar

1. Abra [keyboard-layout-editor.com](https://www.keyboard-layout-editor.com/).
2. Menu **Raw data** (painel lateral) ou **Upload JSON** / importação equivalente.
3. Carregue o ficheiro `keyboard-layout(9).json` desta pasta.
4. Para guardar alterações: **Download JSON** no KLE e substitua o ficheiro no repositório (ou guarde com novo nome e atualize este README).

### Formato

O KLE usa um **array de linhas**; cada linha é um array de teclas. Cada tecla pode ser:

- uma **cadeia de texto** (legenda visível), ou
- um **objeto** com propriedades como `w` (largura em unidades de tecla), `h` (altura), `x` / `y` (posição em grelha), etc.

Documentação informal da sintaxe: painel **Raw data** do próprio site e [repositório do projeto no GitHub](https://github.com/ijprest/keyboard-layout-editor) (licença e código).

### Pinagem (GPIO)

A ligação da matriz **6×7** aos pinos do Raspberry Pi está em [raspberry-pi-4b/pinout.md §6](../raspberry-pi-4b/pinout.md#6-matriz-do-teclado-67--atribuição-de-gpio) (linhas, colunas, cor de fio e conflitos de periférico), com a fonte em código em [`software/hw_platform/keypad_pinout.py`](../../software/hw_platform/keypad_pinout.py). Este layout KLE descreve as **legendas**; o pinout descreve os **fios**.

## Relação com o projeto

Este layout descreve a **grelha de teclas da calculadora científica** (funções tipo `sen`, `cos`, `tan`, `log`, `π`, `Ans`, `Shift`, etc.) para:

- documentação visual do teclado;
- ferramentas que importem JSON do KLE (por exemplo fluxos **KiCad** com plugins que aceitem este formato — confirme sempre o caminho do ficheiro nas preferências do plugin).

## Ficheiros

| Ficheiro | Descrição |
| -------- | ----------- |
| `mapa-teclado.html` | Mapa interativo das 38 teclas e das suas funções (gerado do código). |
| `keyboard-layout(9).json` | Dados crus do layout (export KLE). |
