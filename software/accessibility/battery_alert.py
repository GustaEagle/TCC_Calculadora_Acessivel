"""Monitor de bateria do UPS HAT: avisa por voz quando a carga fica baixa.

Fica numa thread própria, lendo o `UpsMonitor` (INA219 por I2C) a cada
`interval` segundos. Quando a carga cruza o limite de "baixa", emite um alerta
pela voz existente com prioridade CRÍTICA (`SpeechService.alert`), que corta e
precede qualquer outro áudio (ver `software/accessibility/speech.py`).

Anti-repetição (o alerta não pode tocar sem parar): depois de avisar, só volta a
avisar se a carga cair mais `renotify_drop` pontos **ou** se passar
`renotify_interval` segundos. A trava zera quando a bateria se recupera acima do
limite (p. ex. ao voltar a carregar), para um novo ciclo de descarga avisar de
novo.

O limite e os parâmetros são todos injetáveis/por ambiente, para mudar o ponto
de "bateria baixa" sem mexer na lógica.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable

from software.hw_platform.ups import UpsMonitor

logger = logging.getLogger(__name__)

# Limite de "bateria baixa" (percentagem). Fácil de mudar: constante + ambiente.
DEFAULT_LOW_PERCENT = float(os.environ.get("CALC_UPS_LOW_PERCENT", "20"))
# Intervalo entre leituras (s).
DEFAULT_INTERVAL_S = float(os.environ.get("CALC_UPS_POLL_INTERVAL_S", "30"))
# Nova queda (pontos) que justifica repetir o alerta antes do tempo.
DEFAULT_RENOTIFY_DROP = float(os.environ.get("CALC_UPS_RENOTIFY_DROP", "5"))
# Tempo (s) após o qual o alerta se repete mesmo sem nova queda.
DEFAULT_RENOTIFY_INTERVAL_S = float(os.environ.get("CALC_UPS_RENOTIFY_INTERVAL_S", "300"))
# Histerese (pontos acima do limite) para considerar a bateria recuperada.
_RECOVERY_MARGIN = 3.0


def default_alert_message(percent: float) -> str:
    """Texto do aviso de bateria baixa (claro e direto, PRD §13)."""
    return f"Atenção. Bateria baixa, {int(round(percent))} por cento. Conecte o carregador."


class BatteryMonitor:
    """Vigia a bateria do UPS e dispara alertas de voz com anti-repetição."""

    def __init__(
        self,
        speech,
        ups: UpsMonitor | None = None,
        *,
        interval: float = DEFAULT_INTERVAL_S,
        low_percent: float = DEFAULT_LOW_PERCENT,
        renotify_drop: float = DEFAULT_RENOTIFY_DROP,
        renotify_interval: float = DEFAULT_RENOTIFY_INTERVAL_S,
        message_fn: Callable[[float], str] = default_alert_message,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._speech = speech
        self._ups = ups or UpsMonitor(low_percent=low_percent)
        self._interval = interval
        self._low_percent = low_percent
        self._renotify_drop = renotify_drop
        self._renotify_interval = renotify_interval
        self._message_fn = message_fn
        self._clock = clock or time.monotonic

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # Estado da trava anti-repetição.
        self._last_announced_percent: float | None = None
        self._last_announced_at: float | None = None

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

    # --- lógica (testável sem thread) ----------------------------------

    def check(self) -> None:
        """Uma leitura + decisão de alerta. Chamável direto nos testes."""
        status = self._ups.read_status()
        if not status.available or status.battery_percent is None:
            return
        percent = status.battery_percent
        if percent > self._low_percent:
            # Recuperou com folga: rearma para o próximo ciclo de descarga.
            if percent >= self._low_percent + _RECOVERY_MARGIN:
                self._reset_latch()
            return
        if self._should_announce(percent):
            self._announce(percent)

    def _should_announce(self, percent: float) -> bool:
        if self._last_announced_percent is None:
            return True  # primeira vez abaixo do limite
        if percent <= self._last_announced_percent - self._renotify_drop:
            return True  # caiu mais um degrau
        if self._last_announced_at is not None:
            if self._clock() - self._last_announced_at >= self._renotify_interval:
                return True  # passou o intervalo configurado
        return False

    def _announce(self, percent: float) -> None:
        logger.warning("Bateria baixa: %.0f%% (limite %.0f%%)", percent, self._low_percent)
        self._speech.alert(self._message_fn(percent))
        self._last_announced_percent = percent
        self._last_announced_at = self._clock()

    def _reset_latch(self) -> None:
        self._last_announced_percent = None
        self._last_announced_at = None
