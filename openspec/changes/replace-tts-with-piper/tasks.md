## 1. Preparação e decisão

- [ ] 1.1 Medir a **baseline** no Pi: latência entre soltar a tecla e o som com o espeak-ng/pyttsx3 atual, para o "sete", para um resultado longo e para um erro §13. Registrar em `docs/testes/`. Verificar: números anotados para comparação posterior.
- [ ] 1.2 Confirmar no rootfs de build que `py3-onnxruntime` (community v3.24, aarch64) resolve para Python 3.14/musl e mede ~120 MB de closure. Verificar: `apk add --simulate py3-onnxruntime` no chroot lista os pacotes esperados sem erro.
- [ ] 1.3 Registrar a decisão no OpenSpec/PRD antes de codar (esta mudança). Verificar: `proposal.md`, `design.md`, `specs/speech-engine/spec.md` e `specs/rpi-boot-image/spec.md` presentes e coerentes.

## 2. Protótipo no hardware (gate antes de codar o serviço)

- [ ] 2.1 Compilar um wheel `musl/aarch64` de `piper-tts` (tag fixa, via git — o sdist do PyPI é incompleto) num container `alpine:3.24` arm64 ou no próprio Pi, sobre `py3-onnxruntime`. Verificar: `pip install --no-deps <wheel>` e `python3 -c "import piper"` no Pi.
- [ ] 2.2 Rodar a voz `cadu` no Pi (Python 3.14) e sintetizar as frases reais: 38 nomes de tecla, dígitos, os 10 erros §13, avisos 012/013 e resultados longos. Verificar: WAVs gerados e audíveis; nenhuma palavra curta ("é", "pi", "mais") engolida — senão, avaliar pontuação/pausa.
- [ ] 2.3 Medir carga do modelo, latência por frase (tecla e resultado longo), pico de CPU, RAM residente e temperatura. Verificar: latência de tecla ≤ baseline (2.1) com cache; resultado longo dentro do aceitável do PRD; anotado em `docs/testes/`.
- [ ] 2.4 Teste de escuta da `cadu` com as frases reais (equipe). Verificar: inteligibilidade aprovada (PRD §8); se reprovada, reavaliar voz antes de prosseguir (fora do escopo desta mudança se trocar).
- [ ] 2.5 Definir o número de threads do ONNX no Pi 4 e se o cache é pré-aquecido no arranque ou sob demanda (design, Open Questions). Verificar: valores escolhidos com base em 2.3.

## 3. Serviço de voz residente (`software/accessibility/speech.py`)

- [ ] 3.1 Criar o motor residente (import tardio de `piper`/`onnxruntime`): carga assíncrona do modelo `cadu`, `synthesize(text) -> bytes` (PCM S16LE mono) e threads do ONNX limitadas (D2). Verificar: `python -c "import software.accessibility.speech"` **sem** Piper instalado não falha (import tardio).
- [ ] 3.2 Substituir a reprodução por um player raw `aplay -t raw -f S16_LE -c1 -r <sample_rate> -` pela stdin, com grupo de processo próprio e `terminate()` que mata o `aplay` (D3). Verificar: teste com `aplay` falso no PATH (memória `tts-fake-aplay-testing`) confirma o comando e o formato; `terminate()` encerra o player.
- [ ] 3.3 Manter a fila, `_Generation` e a API `say`/`interrupt_and_say`/`stop` intactas, ligando o motor pela `process_factory`/`SpeakProcess` (D1). Verificar: os testes de fila e interrupção existentes passam com um motor injetado (sem Piper real).
- [ ] 3.4 Implementar o cache de frases fixas, aquecido após a carga do modelo, e a reprodução por cache no `say` (D4). Verificar: teste mostra que uma frase do conjunto fixo não chama a síntese quando o cache está quente, e que um resultado numérico chama.
- [ ] 3.5 Implementar o fallback `espeak-ng` + `WRN-011` (motor ausente, modelo ausente, ou durante a carga), sem bloquear a entrada (D6). Verificar: teste com Piper "indisponível" reproduz por espeak-ng, loga `WRN-011` uma vez, e a fila segue.
- [ ] 3.6 Reescrever/retirar os testes específicos do driver pyttsx3 (`_EspeakLikeEngine`, `SpeakWaitsForPlaybackTest`) para o motor residente; adicionar testes de cache e fallback. Verificar: `python -m unittest software.tests.test_speech_service -v` passa sob **fork e forkserver** (memória `pi-python-forkserver`).

## 4. Dependências de desenvolvimento (Docker/CI/host)

- [ ] 4.1 `software/requirements.txt`: remover `pyttsx3`; adicionar `piper-tts` com marcador de ambiente que não quebre o build musl (imagem usa o wheel pré-compilado). Verificar: `pip install -r requirements.txt` funciona no CI (glibc, Python 3.11).
- [ ] 4.2 Script para baixar a voz `cadu` (`.onnx` + `.onnx.json`) com sha256, reutilizável por Docker e imagem. Verificar: script baixa e valida o hash; roda idempotente.
- [ ] 4.3 `Dockerfile`, `docker-compose*.yml`, `Makefile`: remover dependência do `pyttsx3`, instalar `piper-tts` e a voz, manter a ponte de áudio para o host. Verificar: `make up` fala pela voz `cadu` no host Linux.
- [ ] 4.4 Confirmar que `make check` e o CI passam **sem** Piper e **sem** áudio (import tardio, motor injetável). Verificar: `python -m unittest discover -s software/tests -v` verde no CI.

## 5. Imagem Alpine (`system/rpi-os/alpine/`)

- [ ] 5.1 `packages`: adicionar `py3-onnxruntime` (community). Atualizar o comentário da seção de TTS (Piper + cadu; espeak-ng como fonemizador/fallback). Verificar: `test_image_packages.py` (parser) e o `apk add` no chroot incluem o pacote.
- [ ] 5.2 `build-alpine-img.sh`: instalar o wheel do Piper com `--no-deps`, baixar e validar a voz `cadu` (sha256), remover os modelos de outras línguas do `piper-tts` (hebrew/tashkeel, ~25 MB) e o symlink `libespeak.so.1`. Verificar: rootfs contém `piper`, o `.onnx` da cadu e não contém o pyttsx3.
- [ ] 5.3 Trocar o smoke de `pyttsx3.init()` por uma **síntese real** do Piper no chroot (Piper → PCM, sem placa de som). Verificar: o smoke gera PCM não-vazio sob qemu; falha cedo se o Piper não importar no 3.14.
- [ ] 5.4 Atualizar o checklist de hardware do `system/rpi-os/alpine/README.md`: voz `cadu` anuncia offline, interrupção (RF-08) sem `Device busy`, `/tmp` sem sobras, latência e arranque. Verificar: itens presentes no checklist.

## 6. Validação no hardware e documentação

- [ ] 6.1 Gravar a imagem e validar no Pi: voz `cadu` offline; interrupção do `=` corta a fala sem sobrepor; sem `WRN-011` inesperado (Piper carregou); `/tmp` (tmpfs) sem acúmulo. Verificar: checklist do README marcado no aparelho.
- [ ] 6.2 Medir latência (tecla, resultado, erro) e tempo de arranque no hardware; comparar com a baseline (1.1). Verificar: números em `docs/testes/`; RNF-06 não regride de forma inaceitável.
- [ ] 6.3 Atualizar PRD §12, `software/README.md`, `docs/guias/build-img-linux.md` e `openspec/config.yaml`: TTS passa a "Piper (voz cadu), espeak-ng como fonemizador/fallback"; remover as afirmações de que a voz é pyttsx3/espeak. Verificar: `grep -rn pyttsx3 software docs openspec` só aparece em contexto histórico/arquivado.
- [ ] 6.4 Rodar a suíte completa e revisar o diff. Verificar: `python -m unittest discover -s software/tests -v` verde; nenhum consumidor de voz (`app.py`, fronts, `audio_only.py`, `video_watch.py`) alterado.
- [ ] 6.5 Decidir (fora desta mudança) se o apk `espeak-ng` do sistema é removido depois da validação. Verificar: decisão registrada; se mantido, justificativa do fallback anotada.
