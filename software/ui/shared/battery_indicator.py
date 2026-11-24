"""Indicador de bateria na barra de indicadores dos dois fronts (WRN-020).

O aviso por VOZ sai do `BatteryMonitor` (accessibility/battery_alert.py), numa
thread própria. A TELA não pode ser atualizada dessa thread: o Tk só aceita
chamadas do seu próprio laço. Por isso o front consulta `monitor.snapshot()`
periodicamente com `root.after`, no mesmo formato do leitor da matriz
(matrix_input.py), e só redesenha quando o texto muda.

O indicador fica VAZIO com a bateria normal ou sem UPS: a barra de 800x480 do
LCD não tem espaço a desperdiçar, e um percentual sempre aceso distrairia. Só
aparece quando há o que avisar (PRD §13, WRN-020: indicador + «Bateria baixa»).
"""

from __future__ import annotations

from typing import Callable

from software.accessibility.battery_alert import (
    LEVEL_CRITICAL,
    LEVEL_LOW,
    BatteryReading,
)

# Intervalo de consulta da última leitura (ms). A leitura do UPS em si é bem
# mais espaçada (CALC_UPS_POLL_INTERVAL_S); isto só reflete na tela a mais
# recente sem demora perceptível.
POLL_INTERVAL_MS = 1000

# bootstyle do ttkbootstrap para cada nível.
STYLE_LOW = "warning"
STYLE_CRITICAL = "danger"


def battery_indicator(reading: BatteryReading | None) -> tuple[str, str]:
    """(texto, bootstyle) do indicador para uma leitura; texto vazio = escondido."""
    if reading is None or reading.percent is None:
        return "", STYLE_LOW
    percent = int(round(reading.percent))
    if reading.level == LEVEL_CRITICAL:
        return f"BATERIA NO FIM {percent}%", STYLE_CRITICAL
    if reading.level == LEVEL_LOW:
        return f"BATERIA BAIXA {percent}%", STYLE_LOW
    return "", STYLE_LOW


class BatteryIndicatorWatch:
    """Reflete na tela, a cada `interval_ms`, a última leitura do monitor."""

    def __init__(
        self,
        root,
        monitor,
        apply: Callable[[str, str], None],
        interval_ms: int = POLL_INTERVAL_MS,
    ) -> None:
        self.root = root
        self.monitor = monitor
        self.apply = apply
        self.interval_ms = interval_ms
        self._stopped = False
        self._shown: tuple[str, str] | None = None

    def start(self) -> None:
        if self.monitor is None:
            return  # sem UPS (PC sem simulação): nada a mostrar
        self.tick()

    def stop(self) -> None:
        self._stopped = True

    def tick(self) -> None:
        if self._stopped:
            return
        try:
            shown = battery_indicator(self.monitor.snapshot())
            if shown != self._shown:
                self._shown = shown
                self.apply(*shown)
        finally:
            # Reagendado mesmo se o redesenho falhar: o indicador não pode
            # morrer em silêncio.
            self.root.after(self.interval_ms, self.tick)
