## Why

Hoje a voz da calculadora sai do `espeak-ng` através do `pyttsx3` (`software/accessibility/speech.py`, `requirements.txt`, `system/rpi-os/alpine/packages`). O `espeak-ng` é robusto e cabe no arranque rápido (RNF-06), mas soa **formântico e metálico**, o que atrapalha a inteligibilidade exigida pelo PRD §8 — justamente o requisito que serve o usuário com cegueira total, para quem a voz é o canal principal (RF-04, RF-07). O objetivo é uma voz **neural, natural e em português do Brasil**, mantendo o funcionamento **offline** e a política de interrupção (RF-08) que já existe.

O motor escolhido é o **Piper** (`OHF-Voice/piper1-gpl`, pacote `piper-tts`), TTS neural offline sobre `onnxruntime`, com Raspberry Pi 4 (aarch64) como alvo de primeira classe. A voz será a **`pt_BR-cadu-medium`** (22.050 Hz, 1 locutor, dataset CC0), que a equipe já escolheu e possui.

O trabalho não é uma troca de biblioteca linha a linha. Duas coisas o condicionam e estão na base desta proposta:

- **O modelo de processos do `speech.py` precisa mudar.** Hoje cada frase abre um **processo novo** (`_SpeakProcess`), que importa o motor e reinicializa a voz. Repetir isso com o Piper recarregaria um modelo de 63 MB a cada tecla — inviável. O motor tem de ficar **residente**.
- **O Piper não tem pacote pronto para o Alpine (musl).** Não há apk nem wheel `musl`. O `piper-tts` precisa ser **compilado** a partir do git (o `setup.py` usa CMake e embute o `espeak-ng` estaticamente); o `onnxruntime`, porém, **já existe** no repositório `community` do Alpine v3.24 aarch64 (`py3-onnxruntime` 1.24.4), que é a parte mais difícil e vem pronta.

Sem esta mudança, a calculadora continua com uma voz que cumpre a norma "pt-BR offline" na letra, mas não a intenção de **clareza** do PRD.

## What Changes

- **Motor de voz residente no `software/accessibility/speech.py`.** O `SpeechService` — a fila, o contador de geração (`_Generation`) e a política de interrupção — é **preservado**. O que muda por baixo:
  - Um **motor Piper residente** carrega o modelo `cadu` **uma vez** (em segundo plano, para não travar o arranque) e sintetiza frase a frase.
  - A reprodução passa a ser `aplay` lendo áudio **raw** (`-t raw -f S16_LE -c1 -r <sample_rate do .onnx.json>`) pela entrada padrão, sem WAV temporário e sem `os.system`. O grupo de processo e o `terminate()` que silenciam o `aplay` continuam válidos.
  - **Cache de frases fixas**: os nomes de tecla (`SPOKEN_TOKEN_NAMES`, 38), os dígitos, os textos de erro/aviso §13 e os anúncios fixos são sintetizados uma vez após o arranque e reproduzidos do cache. É o que mantém a latência por tecla igual ou melhor que hoje.
  - **Fallback**: se o Piper não estiver disponível (import falha, modelo ausente), o serviço cai para o `espeak-ng` (`--stdout | aplay`), registra `WRN-011` e **não bloqueia a entrada** (RF-08).
- **Voz `pt_BR-cadu-medium` embutida na imagem.** O modelo `.onnx` + `.onnx.json` é baixado no build com **sha256 fixo** (padrão do `build-alpine-img.sh`) e validado; nada é baixado no aparelho (offline).
- **`piper-tts` na imagem por wheel pré-compilado.** Um wheel `musl/aarch64` é compilado a partir da tag do `piper-tts` e instalado com `--no-deps` sobre o `py3-onnxruntime` do apk. O `onnxruntime` **não** vem do pip.
- **`py3-onnxruntime` adicionado a `system/rpi-os/alpine/packages`** (repositório `community`, já disponível).
- **`pyttsx3` removido** de `requirements.txt`: nenhum caminho passa a usá-lo.
- **Ambiente de desenvolvimento (Docker/CI)** atualizado: em glibc, `pip install piper-tts` funciona direto; um script baixa a voz `cadu`; o `Dockerfile` e o `Makefile` deixam de depender do `pyttsx3`.
- **Documentação e decisões registradas** atualizadas: PRD §12, `software/README.md`, `openspec/config.yaml` e a spec `rpi-boot-image` deixam de dizer "TTS via espeak-ng + pyttsx3" e passam a "Piper (voz cadu), com espeak-ng como fonemizador embutido e fallback".

## Capabilities

### New Capabilities
- `speech-engine`: o motor de síntese de voz offline em pt-BR. Cobre a escolha do Piper e da voz `cadu`, o motor **residente** (modelo carregado uma vez, sem processo por frase), a reprodução por `aplay` em áudio raw pela placa padrão do ALSA, o cache de frases fixas, o carregamento não-bloqueante no arranque (RNF-06), o fallback para `espeak-ng` (WRN-011) e a preservação do contrato de fila e interrupção do `SpeechService` (RF-08).

### Modified Capabilities
- `rpi-boot-image`: o requisito "TTS offline em português embutido" hoje exige `espeak-ng` **e** `pyttsx3`. Passa a exigir o **Piper** com a voz `cadu` embutida e offline, o `onnxruntime` do Alpine, e o `espeak-ng` mantido como fonemizador e fallback (o `pyttsx3` deixa de ser exigido).

## Impact

- **Código alterado:**
  - `software/accessibility/speech.py`: motor residente + player raw + cache + fallback. A API pública (`say`, `interrupt_and_say`, `stop`) e a fila/geração **não mudam**.
  - `software/requirements.txt`: remove `pyttsx3`; acrescenta `piper-tts` (com marcador de ambiente para não quebrar o build musl, que usa o wheel pré-compilado).
  - `system/rpi-os/alpine/packages`: acrescenta `py3-onnxruntime`.
  - `system/rpi-os/alpine/build-alpine-img.sh`: instala o wheel do Piper, baixa e valida a voz `cadu` (sha256), remove os modelos de outras línguas embutidos no `piper-tts` (hebraico/árabe, ~25 MB), troca o smoke de `pyttsx3.init()` por uma **síntese real** no chroot, e remove o symlink `libespeak.so.1` (que só servia ao pyttsx3).
  - `Dockerfile`, `docker-compose*.yml`, `Makefile`: dependências de desenvolvimento.
  - `docs/produto/PRD.md` §12, `software/README.md`, `docs/guias/build-img-linux.md`, `openspec/config.yaml`: texto das decisões.
- **Sem alteração:** os 5 consumidores do serviço de voz — `software/app.py`, `software/ui/lcd/app.py`, `software/ui/hdmi/app.py`, `software/audio_only.py`, `software/ui/shared/video_watch.py` — que só chamam `say` / `interrupt_and_say` / `stop`. Também ficam como estão `software/core/`, os textos falados (`ui/shared/keypad.py`, `history.py`, `error_messages.py`) e a saída de áudio no jack (`overlay/etc/asound.conf`, `usercfg.txt`).
- **Testes:** os testes de fila e interrupção do `SpeechService` continuam (com o motor injetável, sem Piper real). Os testes específicos do driver `pyttsx3`/espeak (`_EspeakLikeEngine`, `SpeakWaitsForPlaybackTest`) são reescritos para o motor residente. Entra um teste de cache e de fallback. A suíte segue rodando **sem Piper** no CI (Python 3.11), por import tardio.
- **Dependências:** `+py3-onnxruntime` e closure (~120 MB instalados, medidos no APKINDEX v3.24 aarch64), `+piper-tts` (wheel, ~35–60 MB) e a voz `cadu` (63 MB). O rootfs sai de ~487 MB para ~0,7 GB, dentro da imagem de 2 GB.
- **Requisitos cobertos:** PRD §8 (inteligibilidade), RNF-02 (TTS offline), RF-08 (a interrupção e a não-blocagem da entrada são preservadas), RNF-06 (carga do modelo não bloqueia o arranque) e RNF-04 (a mudança fica isolada em `accessibility/`).
- **Riscos principais:** build do Piper sob qemu (lento, sdist incompleto, Python 3.14 não testado upstream); latência maior em resultados longos; ALSA sem `dmix` (reprodução sequencial); memória e CPU do modelo neural no Pi 4. Detalhados no `design.md`.

## Não-objetivos

- **Não** mudar o **texto** falado, os nomes de tecla, nem o catálogo de mensagens §13. A migração é do **motor**, não do conteúdo.
- **Não** alterar a saída de áudio no jack de 3,5 mm (`asound.conf`/`usercfg.txt`), que é decisão de produto já registrada.
- **Não** remover o `espeak-ng` da imagem nesta mudança: ele é o fonemizador do Piper (embutido no wheel) e o **fallback**. A remoção do apk `espeak-ng` do sistema, se desejada, fica para uma mudança posterior, depois da validação no hardware.
- **Não** treinar nem afinar voz; usa a `cadu` publicada como está.
- **Não** usar GPU/CUDA (o Pi 4 não tem); o `onnxruntime` roda em CPU.
- **Não** ligar o Piper ao download de vozes em execução (`piper.download_voices`): o aparelho é offline; a voz vai embutida na imagem.
- **Não** adotar streaming intra-frase: o Piper entrega o áudio de uma frase inteira de uma vez. A mitigação (tocar "Resultado" do cache enquanto o número é sintetizado) é de implementação, não de escopo.
