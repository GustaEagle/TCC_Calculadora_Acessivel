# Layout de teclado (Keyboard Layout Editor)

Este diretório contém o ficheiro **[keyboard-layout(9).json](keyboard-layout(9).json)** no formato exportado pelo site **[Keyboard Layout Editor](https://www.keyboard-layout-editor.com/)** (KLE).

## Como abrir ou editar

1. Abra [keyboard-layout-editor.com](https://www.keyboard-layout-editor.com/).
2. Menu **Raw data** (painel lateral) ou **Upload JSON** / importação equivalente.
3. Carregue o ficheiro `keyboard-layout(9).json` desta pasta.
4. Para guardar alterações: **Download JSON** no KLE e substitua o ficheiro no repositório (ou guarde com novo nome e atualize este README).

## Formato

O KLE usa um **array de linhas**; cada linha é um array de teclas. Cada tecla pode ser:

- uma **cadeia de texto** (legenda visível), ou
- um **objeto** com propriedades como `w` (largura em unidades de tecla), `h` (altura), `x` / `y` (posição em grelha), etc.

Documentação informal da sintaxe: painel **Raw data** do próprio site e [repositório do projeto no GitHub](https://github.com/ijprest/keyboard-layout-editor) (licença e código).

## Relação com o projeto

Este layout descreve a **grelha de teclas da calculadora científica** (funções tipo `sen`, `cos`, `tan`, `log`, `π`, `Ans`, `Shift`, etc.) para:

- documentação visual do teclado;
- ferramentas que importem JSON do KLE (por exemplo fluxos **KiCad** com plugins que aceitem este formato — confirme sempre o caminho do ficheiro nas preferências do plugin).

## Ficheiros

| Ficheiro | Descrição |
| -------- | ----------- |
| `keyboard-layout(9).json` | Dados crus do layout (export KLE). |
