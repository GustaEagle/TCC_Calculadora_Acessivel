## Context

A motivação está no `proposal.md` (seção Why) e os requisitos em `specs/speech-engine/spec.md`.

O que já existe e condiciona a abordagem:

- **`software/accessibility/speech.py`** é o **único** lugar que conhece o motor de voz. Ele expõe `SpeechService.say()`, `interrupt_and_say()` e `stop()`, e por baixo tem: uma `queue.Queue`, uma thread worker, o contador `_Generation` (descarta anúncios obsoletos após uma interrupção) e um **processo por frase** (`_SpeakProcess`, subclasse de `multiprocessing.Process`). O processo importa `pyttsx3`, inicializa o motor, escolhe a voz pt-BR, sintetiza para um WAV temporário e toca com `os.system("aplay ...")`. O `_SpeakProcess` lidera um grupo de processo próprio para que `terminate()` mate também o `aplay` neto, e usa um diretório de scratch por frase, apagado no `join()`.
- **Os 5 consumidores** (`app.py`, `ui/lcd/app.py`, `ui/hdmi/app.py`, `audio_only.py`, `ui/shared/video_watch.py`) só chamam `say`/`interrupt_and_say`/`stop`. A mudança fica contida no `speech.py`.
- **`process_factory` / `SpeakProcess` (Protocol)** já são o ponto de injeção: o construtor aceita uma fábrica de "processo de fala" duck-typed (`start`/`join`/`is_alive`/`terminate`). Os testes já usam um `_FakeProcess`. É por aqui que o motor residente entra sem reescrever a fila.
- **Saída de áudio (decidida):** `overlay/etc/asound.conf` fixa a placa `Headphones` (jack 3,5 mm do Pi) **pelo nome**, e o PCM padrão do ALSA na imagem é `plug → hw`, **sem `dmix`**. Só um processo abre a placa por vez. O `espeak-ng` já gera 22.050 Hz / mono / 16-bit, e a voz `cadu` também é 22.050 Hz — o formato que chega ao jack não muda.
- **Imagem:** Alpine 3.24.1 aarch64, Python **3.14.7**, `espeak-ng` 1.52, `alsa-utils` (aplay), só ALSA (sem PulseAudio). O `community` v3.24 tem `onnxruntime`/`py3-onnxruntime` **1.24.4** já compilados para musl e Python 3.14 (confirmado no APKINDEX em cache no rootfs de build). O multiprocessing no 3.14 usa **forkserver** por padrão (o dev/CI usam **fork**).
- **`piper-tts` (upstream `OHF-Voice/piper1-gpl`, versão 1.8.0, GPL-3.0):**
  - depende de `onnxruntime>=1,<2` e `pathvalidate`;
  - **embute o próprio `espeak-ng`** (ligado estaticamente via CMake, tag fixa) e os `espeak-ng-data`, usados só como **fonemizador** — a voz é o modelo neural;
  - o **sdist do PyPI é incompleto** (falta `CMakeLists.txt`, `espeakbridge.c`, `espeak-ng-data`): `pip install piper-tts` compila a partir do **git**, não do sdist. Precisa de `build-base`, `cmake`, `git`, `python3-dev`, `scikit-build` — ~200 MB que **não** vão para a imagem final;
  - a extensão C é `abi3` (compatível entre versões de Python), mas o upstream só declara suporte até 3.13 — o 3.14 precisa ser validado;
  - a API Python é `PiperVoice.load(model, config)` + `voice.synthesize(text) -> Iterable[AudioChunk]`, com `AudioChunk.audio_int16_bytes` (PCM S16LE mono). `SessionOptions` permite limitar as threads do ONNX.
- **Armadilha:** o apk chamado **`piper`** no Alpine **não** é o Piper TTS — é um configurador de mouse (libratbag). Nunca `apk add piper`.
- **Voz `pt_BR-cadu-medium`** (repositório `rhasspy/piper-voices`): 22.050 Hz, 1 locutor, `phoneme_type: espeak`, `espeak.voice: pt-br`, dataset CC0, `.onnx` de 63 MB + `.onnx.json`. `inference`: `noise_scale 0.667`, `length_scale 1.0`, `noise_w 0.8`.
- **Frases fixas são um conjunto pequeno e conhecido:** `SPOKEN_TOKEN_NAMES` (38), os 10 dígitos, os 10 textos de `ERROR_MESSAGES` §13, os avisos 012/013 e os anúncios fixos ("Calculadora pronta", "Controle ativo"...). Dá para pré-sintetizar tudo em poucos MB.

## Goals / Non-Goals

**Goals:**
- Voz neural pt-BR (`cadu`) com o **mesmo contrato** de fila e interrupção de hoje (RF-08), sem tocar nos 5 consumidores.
- Motor **residente**: o modelo carrega uma vez, não por frase.
- Arranque não bloqueado pela carga do modelo (RNF-06): "Calculadora pronta" nunca espera o ONNX.
- Degradação segura: sem Piper, cai para `espeak-ng` e a entrada não trava (WRN-011).
- CI e `make check` continuam **sem** Piper nem áudio, por import tardio e motor injetável.

**Non-Goals:**
- Streaming intra-frase (o Piper devolve a frase inteira).
- Interromper uma síntese **em andamento** (a API do Piper não permite abortar; ver D5).
- Remover o `espeak-ng` do sistema (fonemizador + fallback).
- GPU/CUDA; treino de voz; download de voz em execução.

## Decisions

### D1 — O motor residente entra pela `process_factory`, a fila fica intacta

O `SpeechService` continua idêntico: `say`/`interrupt_and_say`/`stop`, `queue.Queue`, worker, `_Generation`, `process_lock`. O que muda é o objeto que a `process_factory` devolve por frase. Hoje é um `_SpeakProcess` (processo). Passa a ser um **handle de reprodução** leve que:

- fala com o **motor residente** já carregado (não recarrega nada);
- expõe a mesma interface duck-typed `SpeakProcess` (`start`, `join`, `is_alive`, `terminate`), para o worker não perceber diferença;
- em `start()`: sintetiza (ou pega do cache, D4) e dispara **um** `aplay`;
- em `terminate()`: mata o `aplay` (grupo de processo, como hoje);
- em `join()`: espera o `aplay` terminar.

*Alternativa rejeitada:* reescrever a fila para chamar o motor direto na thread worker. Perderia o ponto de teste (`process_factory`/`_FakeProcess`) e misturaria síntese com reprodução, dificultando o `terminate()`.

### D2 — Motor residente: `PiperEngine` carregado em segundo plano

Novo componente em `speech.py` (ou submódulo `accessibility/piper_engine.py`), com **import tardio** do `piper`/`onnxruntime`:

- `PiperEngine.load_async()` carrega `PiperVoice.load(model, config)` numa **thread**, para o construtor do `SpeechService` retornar de imediato (RNF-06).
- Enquanto o modelo não terminou de carregar, ou se a carga falhar, o serviço usa o **fallback** (D6). Assim "Calculadora pronta" sai na hora, pelo espeak-ng, mesmo que o ONNX ainda esteja subindo.
- `synthesize(text) -> bytes` concatena os `AudioChunk.audio_int16_bytes` das frases e devolve PCM S16LE mono.
- As threads do `onnxruntime` são limitadas (`SessionOptions.inter_op_num_threads`/`intra_op_num_threads`, ex.: 2–3), para não competir com o Tk e a varredura da matriz. O valor fica configurável.
- Um único `PiperEngine` por `SpeechService` (o serviço já é reusado entre fronts na troca do RF-09).

### D3 — Reprodução: `aplay` lendo raw pela entrada padrão

O player é `aplay -q -t raw -f S16_LE -c 1 -r <sample_rate> -`, recebendo o PCM pela stdin. Motivos:

- o `sample_rate` vem do `.onnx.json` da voz (cadu = 22.050), não é fixado no código;
- dispensa WAV temporário, `os.system` e processo neto — sai a fila de `fala-*`/`tmp*.wav` em `/tmp`;
- o `aplay` usa o PCM padrão do ALSA, que o `asound.conf` já manda para o jack;
- a interrupção continua sendo **matar o `aplay`**. O handle lidera o próprio grupo de processo (como o `_SpeakProcess` de hoje) e `terminate()` faz `killpg(SIGTERM)`.

Como o ALSA não tem `dmix` (Context), **só um `aplay` toca por vez**. A fila já serializa isso (uma frase por vez), e o fallback nunca toca junto com o Piper.

### D4 — Cache de frases fixas, pré-aquecido após o arranque

Um `dict[str, bytes]` (texto → PCM) guarda as frases de conjunto fechado:

- `SPOKEN_TOKEN_NAMES` (38), os dígitos `0..9`, os 10 `ERROR_MESSAGES` §13 com o prefixo falado ("Erro 001. ..."), os avisos 012/013 e os anúncios fixos.
- O pré-aquecimento roda numa thread de baixa prioridade **depois** que o modelo carrega, sem bloquear nada. Até estar pronto, um miss simplesmente sintetiza na hora.
- `say(text)`: se `text` está no cache, o handle só reproduz os bytes (latência ~ a de abrir o `aplay`); senão, sintetiza.
- Resultados e histórico (números, expressões) **não** entram no cache — são dinâmicos.
- **Mitigação de resultados longos:** "Resultado" e "Última resposta" podem sair do cache **imediatamente**, enquanto o número é sintetizado como frase seguinte. É a diferença entre o Piper e o espeak-ng em latência percebida.

*Estimativa:* todas as frases fixas somam poucos MB de PCM em RAM; aceitável no Pi 4 (Context da imagem).

### D5 — Interrupção: descarte por geração + morte do `aplay`; síntese em curso não é abortada

O `interrupt_and_say()` de hoje faz três coisas que **continuam**: `bump()` da geração, limpa a fila e `terminate()` no processo atual. Com o Piper:

- se a frase interrompida já está **tocando**, o `aplay` é morto na hora (igual a hoje);
- se está sendo **sintetizada**, a API do Piper **não** oferece abortar no meio. No pior caso a síntese da frase termina (~100–500 ms para frases curtas) e é **descartada** pelo `_Generation` antes de tocar — o worker checa `is_stale(generation)` e nem abre o `aplay`. O usuário não ouve a frase obsoleta; só espera, no pior caso, o fim de uma síntese curta.
- A síntese pode ser feita **frase a frase** (o Piper já separa por sentença) e a geração é checada **entre frases**, encurtando a janela para textos longos.

*Trade-off aceito:* não há corte no meio de uma síntese. Para as frases fixas (cache) a síntese nem acontece no caminho crítico, então o caso comum (tecla → `=`) já é instantâneo.

### D6 — Fallback `espeak-ng` e WRN-011

Se `import piper`/`onnxruntime` falhar, se o modelo não carregar, ou enquanto ele ainda está carregando, o serviço usa `espeak-ng`:

- reprodução pelo **mesmo** player raw: `espeak-ng -v pt-br --stdout <texto> | aplay ...`, ou `espeak-ng ... -w tmp.wav`;
- registra `WRN-011` (motor TTS degradado) uma vez, sem repetir a cada frase;
- **nunca bloqueia a entrada** (RF-08): a fila segue funcionando.

Isso mantém o dispositivo utilizável se o build do Piper falhar num campo, e cobre a janela de carga do modelo no arranque.

### D7 — Empacotamento na imagem: wheel pré-compilado + voz com sha256

O `build-alpine-img.sh` **não** compila o Piper dentro do fluxo normal (seria lento sob qemu e traria ~200 MB de toolchain). Em vez disso:

- um **wheel `musl/aarch64`** do `piper-tts` é produzido **uma vez** (num container `alpine:3.24` arm64 ou no próprio Pi, a partir da tag fixa do git) e versionado fora da imagem / baixado no build;
- o build instala o wheel com `pip install --no-deps <wheel>` **sobre** o `py3-onnxruntime` do apk (o `onnxruntime` não vem do pip);
- `pathvalidate` (Python puro) vem do pip;
- a voz `cadu` (`.onnx` + `.onnx.json`) é baixada com **sha256 fixo** e validada, no mesmo padrão do minirootfs do script;
- os modelos de outras línguas embutidos no `piper-tts` (`hebrew/`, `tashkeel/` — ~25 MB) são **apagados** do site-packages, já que só pt-BR é usado;
- o **smoke** deixa de ser `pyttsx3.init()` e passa a ser uma **síntese real** no chroot (Piper → PCM), sem placa de som — teste mais forte que o atual e possível sob qemu;
- o symlink `libespeak.so.1` (defensivo, só para o pyttsx3) é removido.

*Alternativa rejeitada:* compilar o Piper no `build-alpine-img.sh`. Torna o build lento e frágil e mistura toolchain com a imagem final.

### D8 — `py3-onnxruntime` pelo apk, não pelo pip

O `onnxruntime` do PyPI **não** tem wheel `musl`, e compilá-lo é enorme. O Alpine `community` v3.24 já traz `py3-onnxruntime` 1.24.4 para Python 3.14/musl. Vai para `system/rpi-os/alpine/packages`, e o wheel do Piper é instalado com `--no-deps` para não puxar o onnxruntime do pip.

*Efeito:* ~120 MB instalados (closure completo: numpy, openblas, protobuf, abseil, icu, sympy — medido no APKINDEX). É o maior item de tamanho da mudança e cabe na imagem de 2 GB.

### D9 — Multiprocessing vs. thread no motor residente

Hoje cada frase é um **processo** (fork/forkserver). Com o motor residente, o modelo vive no **processo principal**; o que é lançado por frase é o **`aplay`** (subprocesso), não um processo Python que recarrega o motor. Assim:

- não se paga fork + import + load por frase;
- no Pi (Python 3.14/forkserver) não há o risco de o filho não herdar o handler de SIGTERM (memória do projeto `pi-python-forkserver`), porque o `aplay` é um subprocesso comum, não um `multiprocessing.Process`;
- a síntese roda na thread worker do serviço; as threads do ONNX são limitadas (D2).

## Risks / Trade-offs

- **[Build do Piper sob qemu é lento e o sdist é incompleto]** → O wheel é compilado **fora** do fluxo do build (D7), uma vez, e reaproveitado. O `CMakeLists` baixa e compila o espeak-ng estático (tag fixa); sob qemu isso leva dezenas de minutos. Mitigação: compilar num container arm64 nativo ou no Pi, e fixar o artefato.
- **[Python 3.14 não é testado pelo upstream]** → a extensão é `abi3`, mas é preciso **validar** a síntese no chroot 3.14 (o smoke de D7 faz exatamente isso) antes de fechar a imagem.
- **[Latência maior em resultados longos]** → o Piper entrega a frase inteira de uma vez; um número grande pode levar centenas de ms a mais que o espeak-ng. Mitigação: "Resultado"/"Última resposta" saem do cache na hora (D4), e a síntese do número segue como frase seguinte.
- **[ALSA sem `dmix`: reprodução sequencial]** → nunca tocar Piper e fallback ao mesmo tempo, senão `Device or resource busy`. A fila já serializa; o código garante um único player ativo.
- **[Memória e CPU do modelo neural no Pi 4]** → +150–300 MB de RAM residente e picos de CPU na síntese. Threads do ONNX limitadas (D2); a síntese fora do caminho crítico via cache. Medir no hardware (tarefa 6).
- **[Interrupção não corta síntese em curso]** → aceito (D5); janela curta por frase, e o caso comum usa cache.
- **[Licença GPL-3.0 do `piper-tts`]** → o `espeak-ng` já é GPL; a `cadu` é CC0. Registrar a proveniência e a licença na imagem. Não afeta o código próprio do projeto (uso, não linkagem estática distribuída no mesmo binário do app).
- **[Tamanho]** → rootfs ~487 MB → ~0,7 GB. Cabe nos 2 GB; monitorar se a imagem crescer com o kernel/firmware.

## Migration Plan

Não há dados nem estado persistido. A migração é de **motor**; o texto falado e a API não mudam.

1. Provar o Piper/`cadu` **no Pi** (protótipo, tarefa 2): medir carga, latência (tecla, resultado longo), CPU, RAM e temperatura, com as frases reais.
2. Trocar o `speech.py` para o motor residente + cache + fallback, mantendo a API e os testes de fila/interrupção.
3. Empacotar (wheel, `py3-onnxruntime`, voz com sha256, smoke de síntese).
4. Validar no hardware; só então decidir se o apk `espeak-ng` do sistema é removido (fica fora desta mudança).

**Rollback:** reverter o commit devolve o `pyttsx3`/`espeak-ng`. Como o `espeak-ng` **permanece** na imagem (fonemizador + fallback), mesmo um Piper quebrado em campo mantém a voz por fallback.

## Open Questions

- **Threads do ONNX no Pi 4:** 2 ou 3? Depende da medição (tarefa 2) versus a carga do Tk + varredura da matriz.
- **Pré-aquecer todo o cache no arranque** ou só sob demanda na primeira ocorrência? A favor de aquecer: latência previsível desde a primeira tecla. Contra: alguns segundos de CPU no arranque (RNF-06). Decidir com a medição.
- **`length_scale`/velocidade:** manter o padrão da `cadu` (1.0) ou acelerar um pouco, como o `rate 175` do pyttsx3 hoje? É ajuste de UX de voz, a validar com a equipe.
- **Remover o apk `espeak-ng` do sistema depois:** vale os 19 MB, ou o fallback justifica mantê-lo? Fica para depois da validação no hardware.
- **Origem do wheel `musl/aarch64`:** compilar no CI (container arm64), no Pi, ou fixar um artefato no repositório de release? Decisão de infraestrutura de build.
