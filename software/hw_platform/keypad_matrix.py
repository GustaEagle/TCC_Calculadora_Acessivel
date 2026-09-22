"""GPIO scanner for the physical 6x7 keypad matrix (RF-05, RF-11).

Polarity validated on the hardware (see keypad_pinout.py and
docs/raspberry-pi-4b/pinout.md §6): one column at a time is driven HIGH, the
rows are inputs with pull-down, the idle columns float. A row read HIGH while
column Cn is active means the switch at CnLm is closed; the 1N4148 in series
with every switch is what makes simultaneous keys safe (no ghosting).

Three layers, so everything but the ioctl is testable without a Pi:

- `MatrixIO` is the only thing that touches GPIO. `GpiodMatrixIO` implements it
  on libgpiod v2 (the py3-libgpiod of the Alpine image, python3-libgpiod on
  Raspberry Pi OS 13) and enforces the electrical invariants itself: rows are
  never outputs, and a second column cannot be driven before the first one
  floats again.
- `scan_once()` and `Debouncer` are pure: they take the IO and the clock as
  arguments.
- `MatrixKeyboard` runs the sweep in a thread and hands every debounced
  press/release to a sink. The fronts attach a sink that only enqueues; the
  Tk side is in ui/shared/matrix_input.py (Tk is not thread-safe).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from software.hw_platform.keypad_pinout import (
    COL_BCM_PINS,
    COL_LINES,
    EMPTY_COORDS,
    GPIOCHIP_LABEL,
    GPIOCHIP_PATH,
    ROW_BCM_PINS,
    ROW_LINES,
    all_lines,
    switch_at,
)

logger = logging.getLogger(__name__)

# Valores de bancada (PRD §12 manda calibrar com o hardware final).
SETTLE_S = 0.001  # espera depois de ativar a coluna, antes de ler as linhas
DEBOUNCE_S = 0.020  # tempo que um estado novo tem de durar para contar
SWEEP_PAUSE_S = 0.002  # pausa entre varreduras: ~100 varreduras/s

CONSUMER = "calculadora-teclado"

Coord = tuple[int, int]  # (coluna, linha), índices de COL_LINES/ROW_LINES


@dataclass(frozen=True)
class KeyEvent:
    """One debounced change of one switch."""

    keycap: str
    coord: str  # "C3L1"
    switch: str  # "SW9"
    pressed: bool
    col_bcm: int
    row_bcm: int
    timestamp: float

    @property
    def state(self) -> str:
        return "pressionado" if self.pressed else "solto"


class MatrixIO(Protocol):
    """The GPIO operations the scanner needs, nothing more."""

    def drive_column(self, bcm: int) -> None: ...

    def float_column(self, bcm: int) -> None: ...

    def read_rows(self) -> tuple[bool, ...]:
        """HIGH/LOW of every row, in ROW_LINES order."""
        ...

    def float_all(self) -> None: ...

    def close(self) -> None: ...


def scan_once(
    io: MatrixIO,
    settle_s: float = SETTLE_S,
    sleep: Callable[[float], None] = time.sleep,
) -> frozenset[Coord]:
    """One full sweep: every closed (col, row) position of the grid.

    The column goes back to floating in a `finally`, so an exception while
    reading never leaves it driven HIGH.
    """
    closed: set[Coord] = set()
    for col, line in enumerate(COL_LINES):
        io.drive_column(line.bcm)
        try:
            sleep(settle_s)
            rows = io.read_rows()
        finally:
            io.float_column(line.bcm)
        closed.update((col, row) for row, high in enumerate(rows) if high)
    return frozenset(closed)


class Debouncer:
    """Time-based debounce per switch: a change counts once it held `debounce_s`.

    A bounce resets the timer of that switch only, so a key that chatters for
    a few milliseconds produces exactly one press. The clock is an argument,
    which lets the tests replay bounces without sleeping.
    """

    def __init__(self, debounce_s: float = DEBOUNCE_S) -> None:
        self.debounce_s = debounce_s
        self._pressed: set[Coord] = set()  # estado confirmado
        self._raw: dict[Coord, bool] = {}  # última leitura crua
        self._since: dict[Coord, float] = {}  # quando a leitura crua mudou
        self._empty_warned: set[Coord] = set()

    @property
    def pressed(self) -> frozenset[Coord]:
        return frozenset(self._pressed)

    def update(self, now: float, closed: frozenset[Coord]) -> list[KeyEvent]:
        self._warn_empty(closed & EMPTY_COORDS)

        events: list[KeyEvent] = []
        watched = (set(closed) | set(self._raw) | self._pressed) - EMPTY_COORDS
        for coord in sorted(watched):
            raw = coord in closed
            if self._raw.get(coord, False) != raw:
                self._raw[coord] = raw
                self._since[coord] = now

            confirmed = coord in self._pressed
            if raw != confirmed and now - self._since[coord] >= self.debounce_s:
                if raw:
                    self._pressed.add(coord)
                else:
                    self._pressed.discard(coord)
                events.append(_event(coord, raw, now))

            if not raw and coord not in self._pressed:
                # Aberto e confirmado aberto: nada a vigiar.
                self._raw.pop(coord, None)
                self._since.pop(coord, None)
        return events

    def _warn_empty(self, empty_closed: frozenset[Coord]) -> None:
        # Uma vez por ocorrência contínua: um curto não pode encher o log.
        for col, row in sorted(empty_closed - self._empty_warned):
            logger.warning(
                "sinal na posição sem switch C%dL%d (GPIO%d -> GPIO%d): "
                "curto ou ponte de solda",
                col, row, COL_LINES[col].bcm, ROW_LINES[row].bcm,
            )
        self._empty_warned = set(empty_closed)


def _event(coord: Coord, pressed: bool, now: float) -> KeyEvent:
    col, row = coord
    sw = switch_at(col, row)
    return KeyEvent(
        keycap=sw.keycap,
        coord=sw.coord,
        switch=sw.switch,
        pressed=pressed,
        col_bcm=COL_LINES[col].bcm,
        row_bcm=ROW_LINES[row].bcm,
        timestamp=now,
    )


class MatrixUnavailable(RuntimeError):
    """No matrix here (no gpiod, no gpiochip0): the normal case on a PC or CI."""


class MatrixOpenError(RuntimeError):
    """The hardware is there but cannot be used (permission, busy line, wrong chip)."""


class GpiodMatrixIO:
    """MatrixIO on libgpiod v2: the 13 lines requested once, as one request.

    Every reconfiguration describes ALL 13 lines. The libgpiod 2.x C API says a
    new line config replaces the old one entirely, and what the Python binding
    does with omitted lines is not something to rely on across 2.x versions: a
    row falling back to "input, no bias" would lose its pull-down silently and
    float, producing phantom keys.

    Offsets are BCM numbers because gpiochip0 on the Pi 4 is the BCM2711
    controller — checked by label before anything is requested.
    """

    def __init__(self, chip_path: str = GPIOCHIP_PATH, consumer: str = CONSUMER) -> None:
        try:
            import gpiod
            from gpiod.line import Bias, Direction, Value
        except ImportError as exc:
            raise MatrixUnavailable(f"pacote gpiod (libgpiod v2) ausente: {exc}") from exc
        if not os.path.exists(chip_path):
            raise MatrixUnavailable(f"{chip_path} não existe")

        self._check_chip(gpiod, chip_path)

        self._value_active = Value.ACTIVE
        self._floating = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.DISABLED)
        self._row_input = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_DOWN)
        self._column_high = gpiod.LineSettings(
            direction=Direction.OUTPUT, bias=Bias.DISABLED, output_value=Value.ACTIVE
        )
        self._active: int | None = None
        self._request = None
        try:
            self._request = gpiod.request_lines(
                chip_path, consumer=consumer, config=self._config(None)
            )
        except OSError as exc:
            raise MatrixOpenError(f"não foi possível requisitar as linhas da matriz: {exc}") from exc

    @staticmethod
    def _check_chip(gpiod, chip_path: str) -> None:
        try:
            chip = gpiod.Chip(chip_path)
        except OSError as exc:  # PermissionError: utilizador fora do grupo gpio
            raise MatrixOpenError(f"não foi possível abrir {chip_path}: {exc}") from exc
        try:
            label = chip.get_info().label
            if label != GPIOCHIP_LABEL:
                raise MatrixOpenError(
                    f"{chip_path} é '{label}', não '{GPIOCHIP_LABEL}' (Raspberry Pi 4): "
                    "o offset não pode ser tomado como número BCM"
                )
            busy = []
            for line in all_lines():
                info = chip.get_line_info(line.bcm)
                if info.used:
                    busy.append(f"{line.name} (GPIO{line.bcm}) em uso por '{info.consumer}'")
            if busy:
                raise MatrixOpenError("linhas da matriz ocupadas: " + "; ".join(busy))
        finally:
            chip.close()

    def _config(self, active_col: int | None) -> dict:
        config = {bcm: self._row_input for bcm in ROW_BCM_PINS}
        for bcm in COL_BCM_PINS:
            config[bcm] = self._column_high if bcm == active_col else self._floating
        return config

    def drive_column(self, bcm: int) -> None:
        if bcm not in COL_BCM_PINS:
            raise ValueError(f"GPIO{bcm} não é coluna da matriz")
        if self._active is not None:
            raise RuntimeError(
                f"coluna GPIO{self._active} ainda ativa: nunca duas colunas em saída"
            )
        # Marcado ANTES do ioctl: se ele falhar a meio, float_column ainda tenta
        # devolver a coluna à entrada.
        self._active = bcm
        self._request.reconfigure_lines(self._config(bcm))

    def float_column(self, bcm: int) -> None:
        if self._active == bcm:
            self._request.reconfigure_lines(self._config(None))
            self._active = None

    def read_rows(self) -> tuple[bool, ...]:
        values = self._request.get_values(list(ROW_BCM_PINS))
        return tuple(value == self._value_active for value in values)

    def float_all(self) -> None:
        """All 13 lines to input with no bias: the safe resting state."""
        if self._request is None:
            return
        self._request.reconfigure_lines(
            {bcm: self._floating for bcm in ROW_BCM_PINS + COL_BCM_PINS}
        )
        self._active = None

    def close(self) -> None:
        if self._request is None:
            return
        try:
            self.float_all()
        finally:
            self._request.release()
            self._request = None


EventSink = Callable[[KeyEvent], None]


class MatrixKeyboard:
    """Sweep the matrix in a thread and hand debounced events to a sink.

    Owned by the entry point for the whole run (one GPIO request per process);
    the fronts attach/detach their sink as they come and go (RF-09). The sweep
    keeps running with no sink attached, so a key held across a front swap is
    not reported as a second press; events with no sink are dropped.
    """

    def __init__(
        self,
        io: MatrixIO,
        settle_s: float = SETTLE_S,
        debounce_s: float = DEBOUNCE_S,
        pause_s: float = SWEEP_PAUSE_S,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._io = io
        self._settle_s = settle_s
        self._pause_s = pause_s
        self._clock = clock
        self._sleep = sleep
        self._debouncer = Debouncer(debounce_s)
        self._sink: EventSink | None = None
        self._sink_lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed = False

    @classmethod
    def open(cls, chip_path: str = GPIOCHIP_PATH, **kwargs) -> MatrixKeyboard | None:
        """A running scanner, or None when this machine has no usable matrix."""
        try:
            io = GpiodMatrixIO(chip_path)
        except MatrixUnavailable as exc:
            logger.info("matriz do teclado inativa: %s", exc)
            return None
        except MatrixOpenError as exc:
            # No Pi isto é defeito de instalação, não o caso normal.
            logger.warning("matriz do teclado indisponível: %s", exc)
            return None
        keyboard = cls(io, **kwargs)
        keyboard.start()
        logger.info("matriz do teclado ativa em %s", chip_path)
        return keyboard

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="keypad-matrix", daemon=True)
        self._thread.start()

    def attach(self, sink: EventSink) -> None:
        with self._sink_lock:
            self._sink = sink

    def detach(self) -> None:
        with self._sink_lock:
            self._sink = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                with self._io_lock:
                    closed = scan_once(self._io, self._settle_s, self._sleep)
                for event in self._debouncer.update(self._clock(), closed):
                    self._deliver(event)
                self._stop.wait(self._pause_s)
        except Exception:
            # Parar em vez de repetir em laço apertado: um erro de ioctl não
            # se resolve sozinho, e o log precisa de uma linha, não de mil.
            logger.exception("falha na leitura da matriz; varredura parada")
            self._safe_float_all()

    def _deliver(self, event: KeyEvent) -> None:
        with self._sink_lock:
            sink = self._sink
        if sink is None:
            logger.debug("tecla sem front ligado, descartada: %s", event)
            return
        try:
            sink(event)
        except Exception:
            logger.exception("o front falhou ao receber %s", event)

    def _safe_float_all(self) -> None:
        try:
            with self._io_lock:
                self._io.float_all()
        except Exception:
            logger.exception("não foi possível devolver as GPIOs da matriz à entrada")

    def close(self) -> None:
        """Stop the sweep, float all 13 lines, release them. Idempotent."""
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        self.detach()
        try:
            if self._thread is not None:
                self._thread.join(timeout=1.0)
        finally:
            try:
                self._safe_float_all()
            finally:
                with self._io_lock:
                    self._io.close()
