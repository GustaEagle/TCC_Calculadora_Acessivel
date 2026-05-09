"""UPS HAT adapter placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpsStatus:
    label: str
    battery_percent: float | None = None
    is_low: bool = False


class UpsMonitor:
    """Stub for Waveshare UPS HAT I2C readings."""

    def read_status(self) -> UpsStatus:
        return UpsStatus(label="local/simulado")
