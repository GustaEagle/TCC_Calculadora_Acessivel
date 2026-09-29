"""Non-blocking text-to-speech feedback service.

Voz neural pt-BR (Piper, voz `cadu`) offline, **residente** em memória e
reproduzida pela placa de áudio padrão do ALSA por meio do `aplay`. Quando o
Piper não está disponível (dependência ausente, modelo ausente ou falha de
carga), o serviço degrada para o `espeak-ng` e registra `WRN-011`, sem travar a
entrada (RF-08).

O contrato de fila e interrupção (RF-08) **não muda**: os fronts continuam
chamando `say` / `interrupt_and_say` / `stop`. O que muda por baixo é o objeto
que a `process_factory` devolve por frase — hoje um handle leve de reprodução
sobre o motor residente, no lugar do processo-por-frase que recarregava a voz.
Ver `openspec/changes/replace-tts-with-piper/design.md` (D1–D9).
"""

from __future__ import annotations

import io
import json
import logging
import os
import queue
import signal
import subprocess
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

logger = logging.getLogger(__name__)

# Nome do arquivo da voz cadu; o `.onnx.json` é o irmão de mesmo nome. A voz é
# embutida na imagem (offline) ou baixada no Docker/host (download-voice.sh).
# Sobrescreva o caminho completo com CALC_PIPER_VOICE.
DEFAULT_VOICE_NAME = "pt_BR-cadu-medium.onnx"
_VOICE_SEARCH_DIRS = (
    "/opt/piper/voices",
    str(Path.home() / ".local/share/piper/voices"),
    str(Path(__file__).resolve().parent / "voices"),
)

# sample_rate da cadu; corrigido a partir do `.onnx.json` quando o modelo carrega.
_CADU_SAMPLE_RATE = 22050

# Nº de threads do onnxruntime no Pi 4 (D2 / Open Question 2.5). Ajustável por
# ambiente; o valor final é decidido pela medição no hardware (tarefa 2.3).
DEFAULT_ONNX_THREADS = int(os.environ.get("CALC_PIPER_THREADS", "2"))

# Binários do sistema (sobrescritíveis para teste — ver `tts-fake-aplay-testing`).
_APLAY = os.environ.get("CALC_APLAY", "aplay")
_ESPEAK = os.environ.get("CALC_ESPEAK", "espeak-ng")
_ESPEAK_VOICE = "pt-br"


@dataclass(frozen=True)
class SpeechMessage:
    text: str
    interrupt: bool = False
    generation: int = 0


class SpeakProcess(Protocol):
    """Minimal process interface SpeechService depends on (duck-typed)."""

    def start(self) -> None: ...
    def join(self, timeout: float | None = None) -> None: ...
    def is_alive(self) -> bool: ...
    def terminate(self) -> None: ...


def _resolve_voice_path() -> Path | None:
    """Primeiro `.onnx` da cadu encontrado (env tem prioridade), ou None."""
    candidates: list[Path] = []
    env = os.environ.get("CALC_PIPER_VOICE")
    if env:
        candidates.append(Path(env))
    candidates.extend(Path(d) / DEFAULT_VOICE_NAME for d in _VOICE_SEARCH_DIRS)
    for path in candidates:
        if path.is_file():
            return path
    return None


class PiperEngine:
    """Motor neural residente (Piper + cadu): carregado UMA vez, fora do caminho quente.

    Faz **import tardio** do `piper`/`onnxruntime`, para o módulo importar sem eles
    (CI, `make check`). O modelo carrega numa thread (`load_async`), de modo que o
    arranque nunca espera o ONNX (RNF-06); enquanto `is_ready` é falso, quem chama
    usa o fallback espeak-ng.
    """

    def __init__(
        self,
        voice_path: str | os.PathLike[str] | None = None,
        num_threads: int = DEFAULT_ONNX_THREADS,
    ) -> None:
        self._voice_path = Path(voice_path) if voice_path else _resolve_voice_path()
        self._num_threads = num_threads
        self._voice = None
        self._sample_rate = _CADU_SAMPLE_RATE
        self._failed = False
        self._ready = threading.Event()      # set só em sucesso
        self._settled = threading.Event()    # set em sucesso OU falha
        self._load_lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def load_async(self) -> None:
        threading.Thread(target=self._load, name="piper-load", daemon=True).start()

    def wait_ready(self, timeout: float | None = None) -> bool:
        """Bloqueia até o modelo carregar OU falhar; devolve se está pronto."""
        self._settled.wait(timeout)
        return self._ready.is_set()

    def _load(self) -> None:
        with self._load_lock:
            if self._settled.is_set():
                return
            try:
                path = self._voice_path
                if not path or not path.is_file():
                    logger.warning("Voz Piper não encontrada (%s); usando fallback.", path)
                    self._failed = True
                    return
                try:
                    from piper import PiperVoice  # import tardio: CI roda sem Piper
                except Exception:
                    logger.warning("piper/onnxruntime indisponível; usando fallback espeak-ng.")
                    self._failed = True
                    return
                self._limit_threads()
                config_path = path.with_name(path.name + ".json")  # .onnx -> .onnx.json
                if config_path.is_file():
                    voice = PiperVoice.load(str(path), config_path=str(config_path))
                else:
                    voice = PiperVoice.load(str(path))
                self._sample_rate = self._read_sample_rate(voice, path)
                self._voice = voice
                self._ready.set()
                logger.info("Voz Piper carregada: %s (%d Hz)", path.name, self._sample_rate)
            except Exception:
                logger.exception("Falha ao carregar a voz Piper; usando fallback.")
                self._failed = True
            finally:
                self._settled.set()

    def _limit_threads(self) -> None:
        # O onnxruntime respeita estas variáveis ao criar a sessão interna do
        # Piper, evitando competir com o Tk e a varredura da matriz (D2).
        os.environ.setdefault("OMP_NUM_THREADS", str(self._num_threads))
        os.environ.setdefault("ORT_NUM_THREADS", str(self._num_threads))

    @staticmethod
    def _read_sample_rate(voice, path: Path) -> int:
        for getter in (
            lambda: voice.config.sample_rate,
            lambda: voice.config.audio.sample_rate,
        ):
            try:
                return int(getter())
            except Exception:
                pass
        try:  # último recurso: ler o próprio .onnx.json
            cfg = json.loads(path.with_name(path.name + ".json").read_text())
            return int(cfg["audio"]["sample_rate"])
        except Exception:
            return _CADU_SAMPLE_RATE

    def synthesize(self, text: str) -> bytes:
        """PCM S16LE mono da frase, concatenando os chunks do Piper."""
        voice = self._voice
        if voice is None:
            raise RuntimeError("PiperEngine.synthesize chamado antes de o modelo carregar")
        chunks: list[bytes] = []
        for chunk in voice.synthesize(text):
            data = getattr(chunk, "audio_int16_bytes", None)
            if data is None:
                array = getattr(chunk, "audio_int16_array", None)
                data = array.tobytes() if array is not None else None
            if data:
                chunks.append(data)
        return b"".join(chunks)


def _espeak_pcm(text: str) -> tuple[bytes, int]:
    """Fallback: sintetiza com espeak-ng e devolve (PCM S16LE mono, sample_rate).

    O espeak-ng gera WAV pela stdout (`--stdout`); a gente lê o cabeçalho com o
    módulo `wave` e devolve o PCM cru, para o mesmo player raw tocar (D6).
    """
    try:
        out = subprocess.run(
            [_ESPEAK, "-v", _ESPEAK_VOICE, "--stdout", text],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        logger.exception("Falha no fallback espeak-ng para '%s'", text)
        return b"", _CADU_SAMPLE_RATE
    try:
        with wave.open(io.BytesIO(out), "rb") as wav:
            return wav.readframes(wav.getnframes()), wav.getframerate()
    except (wave.Error, EOFError):
        logger.warning("espeak-ng devolveu áudio ilegível para '%s'", text)
        return b"", _CADU_SAMPLE_RATE


class _RawPlaybackProcess:
    """Uma frase: sintetiza (ou pega do cache) e toca o PCM por UM `aplay` lendo
    raw S16LE mono pela stdin. Duck-types `SpeakProcess`, então o worker não muda.

    `terminate()` mata o `aplay` pelo grupo de processo próprio (como o antigo
    `_SpeakProcess`), o que sustenta a interrupção (RF-08). A síntese em curso não
    é abortável (D5); por isso, quando `terminate()` chega antes de o `aplay`
    começar, a reprodução é simplesmente descartada.
    """

    def __init__(self, produce: Callable[[], tuple[bytes, int]]) -> None:
        # produce() -> (pcm_bytes, sample_rate); roda na thread do start().
        self._produce = produce
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._done = threading.Event()
        self._terminated = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="tts-play", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            if self._terminated.is_set():
                return
            pcm, sample_rate = self._produce()
            if self._terminated.is_set() or not pcm:
                return
            cmd = [_APLAY, "-q", "-t", "raw", "-f", "S16_LE", "-c", "1",
                   "-r", str(sample_rate), "-"]
            kwargs = dict(
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if hasattr(os, "setsid"):
                kwargs["start_new_session"] = True  # grupo próprio: terminate() só mata o aplay
            with self._lock:
                if self._terminated.is_set():
                    return
                self._proc = subprocess.Popen(cmd, **kwargs)
            try:
                self._proc.communicate(pcm)
            except (BrokenPipeError, OSError):
                pass  # aplay morto (terminate) no meio da escrita
        except Exception:
            logger.exception("Falha ao reproduzir áudio")
        finally:
            self._done.set()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def is_alive(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._done.is_set()

    def terminate(self) -> None:
        self._terminated.set()
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            killed = False
            if hasattr(os, "killpg"):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    killed = True
                except (ProcessLookupError, OSError):
                    pass
            if not killed:
                try:
                    proc.terminate()
                except OSError:
                    pass
        self._done.set()


def default_fixed_phrases() -> list[str]:
    """Frases de conjunto fechado pré-sintetizadas no cache (D4): nomes de tecla,
    dígitos, as linhas de erro/aviso §13 como faladas e os anúncios fixos.

    Import tardio de `ui.shared` para não criar dependência de import entre
    `accessibility` e a UI; um conjunto ausente só significa menos cache, nunca
    um erro.
    """
    phrases: list[str] = []
    try:
        from software.ui.shared.keypad import (
            SPOKEN_TOKEN_NAMES,
            NO_FUNCTION_SPEECH,
            KEYPAD_SHOWN_SPEECH,
            KEYPAD_HIDDEN_SPEECH,
        )
        phrases.extend(SPOKEN_TOKEN_NAMES.values())
        phrases.extend([NO_FUNCTION_SPEECH, KEYPAD_SHOWN_SPEECH, KEYPAD_HIDDEN_SPEECH])
    except Exception:
        logger.debug("keypad indisponível para o pré-cache", exc_info=True)
    try:
        from software.ui.shared.error_messages import ERROR_MESSAGES, spoken_priority_prefix
        for code, msg in ERROR_MESSAGES.items():
            # Mesmo formato falado que os fronts usam (ui/lcd/app.py).
            phrases.append(f"{spoken_priority_prefix(code)} {code.split('-')[-1]}. {msg}")
    except Exception:
        logger.debug("error_messages indisponível para o pré-cache", exc_info=True)
    phrases.extend(str(d) for d in range(10))
    phrases.extend([
        "Calculadora pronta",
        "Calculadora pronta. Saida no monitor.",
        "Calculadora pronta. Sem video disponivel, modo somente audio.",
        "Controle ativo", "Controle desativado",
        "Shift ativo", "Shift desativado",
        "Histórico fechado", "Substituindo",
    ])
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        if phrase and phrase not in seen:
            seen.add(phrase)
            unique.append(phrase)
    return unique


class _Generation:
    """Tracks the "latest valid" interruption generation.

    Every interrupt_and_say() bump()s the counter. A message stamped with an
    older generation is stale even if it was already dequeued by the worker
    before the interrupt arrived (closes the race that made interruption feel
    inconsistent: without this, a message that slipped past the queue clear
    but hadn't started its process yet would still play in full).
    """

    def __init__(self) -> None:
        self._value = 0
        self._lock = threading.Lock()

    def current(self) -> int:
        with self._lock:
            return self._value

    def bump(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def is_stale(self, generation: int) -> bool:
        with self._lock:
            return generation < self._value


class SpeechService:
    """Fila de TTS não-bloqueante, offline em pt-BR, com interrupção (RF-08).

    Por baixo usa um `PiperEngine` residente + cache de frases fixas + fallback
    espeak-ng. A fila, o `_Generation` e a API pública são preservados.
    """

    def __init__(
        self,
        enabled: bool = True,
        process_factory: Callable[[str], SpeakProcess] | None = None,
        *,
        engine: PiperEngine | None = None,
        fixed_phrases: list[str] | None = None,
        warm_cache: bool = True,
    ) -> None:
        self.enabled = enabled
        self._cache: dict[str, bytes] = {}
        self._cache_rate = _CADU_SAMPLE_RATE
        self._degraded_logged = False
        self._degraded_lock = threading.Lock()

        if process_factory is not None:
            # Injeção direta (testes de fila/interrupção): motor não é obrigatório.
            self._engine = engine
            self._process_factory = process_factory
        else:
            self._engine = engine if engine is not None else PiperEngine()
            self._engine.load_async()
            self._process_factory = self._default_factory
            if warm_cache:
                phrases = fixed_phrases if fixed_phrases is not None else default_fixed_phrases()
                self._start_cache_warm(phrases)

        self._queue: queue.Queue[SpeechMessage | None] = queue.Queue()
        self._current_process: SpeakProcess | None = None
        self._process_lock = threading.Lock()
        self._generation = _Generation()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # --- motor + cache + fallback --------------------------------------------

    def _default_factory(self, text: str) -> SpeakProcess:
        return _RawPlaybackProcess(lambda: self._produce(text))

    def _produce(self, text: str) -> tuple[bytes, int]:
        """(PCM, sample_rate) para a frase: cache, senão Piper, senão espeak-ng."""
        engine = self._engine
        if engine is not None and engine.is_ready:
            cached = self._cache.get(text)
            if cached is not None:
                return cached, self._cache_rate
            try:
                pcm = engine.synthesize(text)
                if pcm:
                    return pcm, engine.sample_rate
            except Exception:
                logger.exception("Falha na síntese Piper de '%s'; caindo para espeak-ng", text)
        elif engine is None or engine.failed:
            # Motor ausente ou com falha de carga: degradação real -> WRN-011.
            # (Enquanto o modelo ainda carrega é transitório e não avisa.)
            self._log_degraded_once()
        return _espeak_pcm(text)

    def _log_degraded_once(self) -> None:
        with self._degraded_lock:
            if self._degraded_logged:
                return
            self._degraded_logged = True
        logger.warning("WRN-011 motor TTS neural indisponível; usando espeak-ng (fallback).")

    def _start_cache_warm(self, phrases: list[str]) -> None:
        if not phrases:
            return
        threading.Thread(
            target=self._warm_cache, args=(list(phrases),), name="tts-warm", daemon=True
        ).start()

    def _warm_cache(self, phrases: list[str]) -> None:
        engine = self._engine
        if engine is None:
            return
        wait_ready = getattr(engine, "wait_ready", None)
        if wait_ready is not None:
            wait_ready()  # espera o modelo carregar (ou falhar), sem travar nada crítico
        if not engine.is_ready:
            return
        self._cache_rate = engine.sample_rate
        for text in phrases:
            if not text or text in self._cache:
                continue
            try:
                pcm = engine.synthesize(text)
                if pcm:
                    self._cache[text] = pcm
            except Exception:
                logger.exception("Falha ao pré-sintetizar '%s'", text)
        logger.info("Cache de voz aquecido: %d frases", len(self._cache))

    # --- API pública (inalterada) --------------------------------------------

    def say(self, text: str) -> None:
        if not text:
            return
        self._queue.put(SpeechMessage(text=text, generation=self._generation.current()))

    def interrupt_and_say(self, text: str) -> None:
        if not text:
            return
        generation = self._generation.bump()
        self._clear_queue()
        with self._process_lock:
            if self._current_process is not None and self._current_process.is_alive():
                self._current_process.terminate()
        self._queue.put(SpeechMessage(text=text, interrupt=True, generation=generation))

    def stop(self) -> None:
        with self._process_lock:
            if self._current_process is not None and self._current_process.is_alive():
                self._current_process.terminate()
        self._queue.put(None)

    def _clear_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self) -> None:
        logger.debug("Speech worker thread started")
        while True:
            message = self._queue.get()
            if message is None:
                logger.debug("Received stop signal")
                break

            if self._generation.is_stale(message.generation):
                logger.debug("Skipping stale message: '%s'", message.text)
                continue

            logger.debug("Processing message: '%s'", message.text)
            process = self._process_factory(message.text)
            with self._process_lock:
                self._current_process = process
            process.start()
            process.join()
            with self._process_lock:
                self._current_process = None
            logger.debug("Speech finished or terminated")
