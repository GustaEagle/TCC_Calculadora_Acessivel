"""Controle de volume do áudio do sistema (ALSA), partilhado pelos fronts.

O som da calculadora sai pelo `aplay` sobre o ALSA (ver
`software/accessibility/speech.py`); o volume é o do próprio mixer ALSA, ajustado
pelo `amixer` (pacote `alsa-utils`, já presente na imagem — ver
`system/rpi-os/alpine/packages`). Mexer no mixer do sistema, em vez de aplicar um
ganho próprio no caminho do áudio, mantém UM único gerenciador de áudio: o mesmo
nível vale para a voz neural (Piper) e para o fallback espeak-ng, sem um segundo
sistema paralelo.

O binário, o controle do mixer e o passo são sobrescritíveis por ambiente, para o
limite/incremento ser fácil de mudar depois e para os testes usarem um `amixer`
falso no PATH (mesmo princípio do `CALC_APLAY`).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)

# Binário e controle do mixer (sobrescritíveis — teste e hardware variam).
_AMIXER = os.environ.get("CALC_AMIXER", "amixer")
# "Master" é o controle padrão; na saída HDMI do Pi pode ser "PCM" ou "HDMI".
# Troca por CALC_MIXER_CONTROL sem tocar no código.
_DEFAULT_CONTROL = os.environ.get("CALC_MIXER_CONTROL", "Master")

# Passo de cada aumento/diminuição, em pontos percentuais. Ajustável por ambiente.
_DEFAULT_STEP = int(os.environ.get("CALC_VOLUME_STEP", "10"))

_MIN_PERCENT = 0
_MAX_PERCENT = 100

# `amixer` imprime o nível por canal como "... [75%] [on]"; pegamos o primeiro.
_PERCENT_RE = re.compile(r"\[(\d{1,3})%\]")


def _clamp(percent: int) -> int:
    return max(_MIN_PERCENT, min(_MAX_PERCENT, percent))


class VolumeController:
    """Ajusta o volume do mixer ALSA por incrementos fixos e seguros.

    Todos os métodos devolvem o novo nível (0–100) ou `None` quando o mixer não
    está disponível (sem `amixer`, sem placa, controle inexistente): nesse caso
    quem chama anuncia "volume indisponível" em vez de inventar um número.
    """

    def __init__(
        self,
        control: str | None = None,
        step: int = _DEFAULT_STEP,
        *,
        runner=subprocess.run,
    ) -> None:
        self._control = control or _DEFAULT_CONTROL
        self._step = max(1, step)
        self._run = runner  # injetável para teste

    def current(self) -> int | None:
        """Nível atual do mixer (0–100), ou None se não der para ler."""
        out = self._amixer("get", self._control)
        return self._parse_percent(out)

    def set_percent(self, percent: int) -> int | None:
        """Define o nível, limitado a [0, 100]. Devolve o nível efetivo."""
        target = _clamp(percent)
        out = self._amixer("set", self._control, f"{target}%")
        if out is None:
            return None
        # Preferimos o valor relatado pelo próprio amixer; se não vier, o alvo.
        reported = self._parse_percent(out)
        return reported if reported is not None else target

    def increase(self) -> int | None:
        return self._step_from_current(+self._step)

    def decrease(self) -> int | None:
        return self._step_from_current(-self._step)

    # ------------------------------------------------------------------

    def _step_from_current(self, delta: int) -> int | None:
        current = self.current()
        if current is None:
            return None
        return self.set_percent(current + delta)

    def _amixer(self, *args: str) -> str | None:
        """Roda `amixer -M <args>` e devolve a stdout, ou None em falha.

        `-M` usa a escala mapeada (percepção mais linear do volume). Qualquer
        erro (binário ausente, controle inexistente) vira None, nunca exceção:
        um volume que não ajusta não pode derrubar a entrada da calculadora.
        """
        cmd = [_AMIXER, "-M", *args]
        try:
            proc = self._run(cmd, capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            logger.warning("amixer %s falhou: %s", " ".join(args), exc)
            return None
        return proc.stdout

    @staticmethod
    def _parse_percent(output: str | None) -> int | None:
        if not output:
            return None
        match = _PERCENT_RE.search(output)
        if match is None:
            return None
        return _clamp(int(match.group(1)))
