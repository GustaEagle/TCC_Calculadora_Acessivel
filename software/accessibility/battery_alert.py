"""Monitor de bateria do UPS HAT: avisa por voz e na tela quando a carga acaba.

Fica numa thread própria, lendo o `UpsMonitor` (INA219 por I2C) a cada
`interval` segundos. Há DOIS níveis, ambos registrados no log e no catálogo
com o código WRN-020 do PRD §13, com urgência diferente:

- **baixa** (`low_percent`, 20% por padrão): «Bateria baixa, 18 por cento.
  Conecte o carregador.»
- **no fim** (`critical_percent`, 10% por padrão): «Bateria no fim, 7 por
  cento. A calculadora vai desligar. Conecte o carregador agora.»

A frase FALADA não diz o número do aviso: para quem ouve, «Aviso 020» não
acrescenta nada à ação que importa, que é conectar o carregador.

Cada aviso começa por um SINAL SONORO - 2 bipes na bateria baixa, 3 mais
agudos e rápidos no fim - e segue com a frase. Os dois saem com prioridade
CRÍTICA (`SpeechService.alert`), que corta e precede qualquer outro áudio (ver
`software/accessibility/speech.py`).

Anti-repetição (o alerta não pode tocar sem parar): depois de avisar, só volta a
avisar se a carga cair mais `renotify_drop` pontos, se passar o intervalo de
repetição (mais curto no nível "no fim") ou se a bateria PASSAR de baixa a no
fim. A trava zera quando a bateria se recupera com folga acima do limite (p. ex.
ao voltar a carregar), para um novo ciclo de descarga avisar de novo.

A última leitura fica disponível em `snapshot()`, que os fronts consultam no
laço do Tk para mostrar o indicador na tela - a thread do monitor nunca toca no
Tk.

O limite e os parâmetros são todos injetáveis/por ambiente, para mudar o ponto
de "bateria baixa" sem mexer na lógica.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable

from software.hw_platform.ups import UpsMonitor

logger = logging.getLogger(__name__)

# Limite de "bateria baixa" (percentagem). Fácil de mudar: constante + ambiente.
DEFAULT_LOW_PERCENT = float(os.environ.get("CALC_UPS_LOW_PERCENT", "20"))
# Limite de "bateria no fim": a calculadora está prestes a desligar.
DEFAULT_CRITICAL_PERCENT = float(os.environ.get("CALC_UPS_CRITICAL_PERCENT", "10"))
# Intervalo entre leituras (s).
DEFAULT_INTERVAL_S = float(os.environ.get("CALC_UPS_POLL_INTERVAL_S", "30"))
# Nova queda (pontos) que justifica repetir o alerta antes do tempo.
DEFAULT_RENOTIFY_DROP = float(os.environ.get("CALC_UPS_RENOTIFY_DROP", "5"))
# Tempo (s) após o qual o alerta se repete mesmo sem nova queda.
DEFAULT_RENOTIFY_INTERVAL_S = float(os.environ.get("CALC_UPS_RENOTIFY_INTERVAL_S", "300"))
# No nível "no fim" o desligamento está perto: repete mais vezes.
DEFAULT_CRITICAL_RENOTIFY_INTERVAL_S = float(
    os.environ.get("CALC_UPS_CRITICAL_RENOTIFY_INTERVAL_S", "60")
)
# Histerese (pontos acima do limite) para considerar a bateria recuperada.
_RECOVERY_MARGIN = 3.0

# Sinal sonoro antes da frase (bipes): mais bipes, e mais agudos, no fim.
LOW_ALERT_BEEPS = 2
CRITICAL_ALERT_BEEPS = 3

# Código do catálogo do PRD §13 para os dois níveis.
BATTERY_WARNING_CODE = "WRN-020"

LEVEL_OK = "ok"
LEVEL_LOW = "low"
LEVEL_CRITICAL = "critical"


@dataclass(frozen=True)
class BatteryReading:
    """Última leitura, para a tela. `level` None = ainda sem leitura válida."""

    level: str | None = None
    percent: float | None = None


def default_alert_message(percent: float) -> str:
    """Frase falada do aviso de bateria baixa (WRN-020)."""
    return f"Bateria baixa, {int(round(percent))} por cento. Conecte o carregador."


def default_critical_message(percent: float) -> str:
    """Frase falada do aviso de bateria no fim: o desligamento está perto."""
    return (
        f"Bateria no fim, {int(round(percent))} por cento. "
        "A calculadora vai desligar. Conecte o carregador agora."
    )


class BatteryMonitor:
    """Vigia a bateria do UPS e dispara alertas de voz com anti-repetição."""

    def __init__(
        self,
        speech,
        ups: UpsMonitor | None = None,
        *,
        interval: float = DEFAULT_INTERVAL_S,
        low_percent: float = DEFAULT_LOW_PERCENT,
        critical_percent: float = DEFAULT_CRITICAL_PERCENT,
        renotify_drop: float = DEFAULT_RENOTIFY_DROP,
        renotify_interval: float = DEFAULT_RENOTIFY_INTERVAL_S,
        critical_renotify_interval: float = DEFAULT_CRITICAL_RENOTIFY_INTERVAL_S,
        message_fn: Callable[[float], str] = default_alert_message,
        critical_message_fn: Callable[[float], str] = default_critical_message,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._speech = speech
        self._ups = ups or UpsMonitor(low_percent=low_percent)
        self._interval = interval
        self._low_percent = low_percent
        # "No fim" nunca acima de "baixa", mesmo com ambiente mal configurado.
        self._critical_percent = min(critical_percent, low_percent)
        self._renotify_drop = renotify_drop
        self._renotify_interval = renotify_interval
        self._critical_renotify_interval = critical_renotify_interval
        self._message_fn = message_fn
        self._critical_message_fn = critical_message_fn
        self._clock = clock or time.monotonic

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # Estado da trava anti-repetição.
        self._last_announced_percent: float | None = None
        self._last_announced_at: float | None = None
        self._last_announced_level: str | None = None
        # Última leitura, lida pelos fronts noutra thread (snapshot()).
        self._reading_lock = threading.Lock()
        self._reading = BatteryReading()

    # --- ciclo de vida -------------------------------------------------

    def start(self) -> None:
        """Começa a vigiar numa thread daemon (não bloqueia o arranque)."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="battery-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.1, min(1.0, self._interval)))

    def _loop(self) -> None:
        # Espera ANTES da primeira leitura: num processo de vida curta (testes,
        # troca rápida de front) o monitor nunca chega a tocar no hardware.
        while not self._stop.wait(self._interval):
            try:
                self.check()
            except Exception:  # uma falha de leitura não pode matar o monitor
                logger.exception("Falha ao checar a bateria do UPS")

    # --- leitura para a tela -------------------------------------------

    def snapshot(self) -> BatteryReading:
        """Última leitura (nível e carga). Seguro de chamar de qualquer thread."""
        with self._reading_lock:
            return self._reading

    # --- lógica (testável sem thread) ----------------------------------

    def check(self) -> None:
        """Uma leitura + decisão de alerta. Chamável direto nos testes."""
        status = self._ups.read_status()
        if not status.available or status.battery_percent is None:
            return
        percent = status.battery_percent
        level = self._classify(percent)
        with self._reading_lock:
            self._reading = BatteryReading(level=level, percent=percent)

        if level == LEVEL_OK:
            self._reset_latch()
            return
        # Na faixa de histerese (acima do limite mas sem folga) o indicador
        # continua aceso, mas a voz não repete um aviso de bateria baixa.
        if percent > self._low_percent:
            return
        if self._should_announce(level, percent):
            self._announce(level, percent)

    def _classify(self, percent: float) -> str:
        """Nível da carga, com histerese para não piscar perto dos limites."""
        previous = self._reading.level
        if percent <= self._critical_percent:
            return LEVEL_CRITICAL
        if previous == LEVEL_CRITICAL and percent < self._critical_percent + _RECOVERY_MARGIN:
            return LEVEL_CRITICAL
        if percent <= self._low_percent:
            return LEVEL_LOW
        if previous in (LEVEL_LOW, LEVEL_CRITICAL) and percent < self._low_percent + _RECOVERY_MARGIN:
            return LEVEL_LOW
        return LEVEL_OK

    def _should_announce(self, level: str, percent: float) -> bool:
        if self._last_announced_percent is None:
            return True  # primeira vez abaixo do limite
        if level == LEVEL_CRITICAL and self._last_announced_level != LEVEL_CRITICAL:
            return True  # passou de "baixa" para "no fim": avisa já
        if percent <= self._last_announced_percent - self._renotify_drop:
            return True  # caiu mais um degrau
        interval = (
            self._critical_renotify_interval
            if level == LEVEL_CRITICAL
            else self._renotify_interval
        )
        if self._last_announced_at is not None:
            if self._clock() - self._last_announced_at >= interval:
                return True  # passou o intervalo configurado
        return False

    def _announce(self, level: str, percent: float) -> None:
        if level == LEVEL_CRITICAL:
            logger.warning(
                "%s bateria no fim: %.0f%% (limite %.0f%%)",
                BATTERY_WARNING_CODE, percent, self._critical_percent,
            )
            self._speech.alert(self._critical_message_fn(percent), beeps=CRITICAL_ALERT_BEEPS)
        else:
            logger.warning(
                "%s bateria baixa: %.0f%% (limite %.0f%%)",
                BATTERY_WARNING_CODE, percent, self._low_percent,
            )
            self._speech.alert(self._message_fn(percent), beeps=LOW_ALERT_BEEPS)
        self._last_announced_percent = percent
        self._last_announced_at = self._clock()
        self._last_announced_level = level

    def _reset_latch(self) -> None:
        self._last_announced_percent = None
        self._last_announced_at = None
        self._last_announced_level = None
