# `wheels/` — o wheel do Piper para a imagem Alpine

Esta pasta guarda **um único artefato de build**: o wheel do `piper-tts`
compilado para **musl/aarch64**, que o build da imagem instala no rootfs.

```
piper_tts-1.8.0-cp39-abi3-linux_aarch64.whl   (~34 MB, NÃO versionado)
```

O `.whl` está no [`.gitignore`](../../../.gitignore); só este README é versionado.
Ele é tratado como o `.img`: **reproduzível por script, logo não entra no git.**

## Por que este arquivo precisa existir

A voz neural do produto é o **Piper** (motor ONNX + voz `cadu`, pt-BR). O
problema é a combinação de plataforma:

| | |
| --- | --- |
| A imagem é **Alpine Linux** | biblioteca C = **musl** |
| O alvo é **Raspberry Pi 4B** | arquitetura = **aarch64** |

E o PyPI **não publica wheel musl/aarch64** do `piper-tts`. Verificado na versão
1.8.0 — os arquivos disponíveis são:

```
piper_tts-1.8.0-cp39-abi3-manylinux_2_17_aarch64...whl   <- aarch64, mas glibc
piper_tts-1.8.0-cp39-abi3-manylinux_2_17_x86_64...whl
piper_tts-1.8.0-cp39-abi3-macosx / win_amd64 ...
piper_tts-1.8.0.tar.gz                                   <- sdist incompleto
```

As releases do GitHub do `OHF-Voice/piper1-gpl` publicam exatamente os mesmos
arquivos. Ou seja: **não existe wheel pronto que sirva**, e o `sdist` do PyPI é
incompleto (não traz o que é preciso para ligar o espeak-ng). A única via é
compilar da tag do git — é o que
[`scripts/build-piper-wheel.sh`](../../../scripts/build-piper-wheel.sh) faz.

Um wheel `manylinux` (glibc) **não** funciona numa imagem musl: o binário
procuraria uma libc que não existe ali.

## Como gerar

```bash
make piper-wheel        # a partir da raiz do repositório
```

Compila num Alpine aarch64 emulado (Docker `--platform linux/arm64`, ou um
chroot com `qemu-aarch64-static` se não houver Docker) e deixa o `.whl` aqui.

É **lento** — compila o espeak-ng inteiro sob emulação. Em troca, você faz isso
**uma vez**: o wheel é `abi3`, serve para qualquer Python 3.x da imagem, e todos
os builds seguintes o reaproveitam.

## Como a imagem consome

Depois de gerado, não precisa passar nada:

```bash
make rpi-img            # encontra o wheel desta pasta sozinho
```

O `Makefile` define `PIPER_WHEEL` apontando para o glob desta pasta, e o
`build-alpine-img.sh` o instala com `--no-deps` — porque o **onnxruntime vem do
`apk`** (`py3-onnxruntime`), nunca do pip. Se a pasta estiver vazia, o build para
com uma mensagem pedindo `make piper-wheel`; ele nunca cai calado no espeak-ng.

## Dois detalhes que confundem

**A tag diz `linux_aarch64`, não `musllinux_*_aarch64`.** O binário *é* musl de
verdade (compilado dentro do Alpine 3.24), só não passou pelo `auditwheel`, que
seria o responsável por colocar o rótulo `musllinux`. Como a instalação é por
caminho de arquivo, na mesma versão do Alpine que compilou, o pip aceita a tag
genérica. Não é problema — mas explica a diferença se você comparar com a
documentação antiga.

**O build exige `linux-headers`.** O espeak-ng inclui `<linux/limits.h>`, que no
Alpine só existe com esse pacote — em distros glibc ele vem de carona no pacote
de dev da libc. Sem ele a compilação morre com `fatal error: linux/limits.h: No
such file or directory`, e o `ninja` reporta apenas um genérico
`subcommand failed`. Já está na lista de dependências do script; fica registrado
aqui porque o sintoma esconde a causa.

## Se apagar esta pasta

Nada se perde de permanente: rode `make piper-wheel` outra vez. Só custa o tempo
da compilação emulada.
