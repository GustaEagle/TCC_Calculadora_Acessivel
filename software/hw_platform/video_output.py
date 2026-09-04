"""Point the X server at the panel that should show the UI.

Detecting the change (display.py) is only half of it: X keeps driving whatever
output it configured at startup, so a monitor plugged in later stays dark until
someone enables it. `xrandr` does that without restarting the X server, which
is what lets the swap happen with the calculator still running.

Everything here is best effort. Off the Pi there is no X server and no xrandr,
and the calls simply report failure instead of raising - a developer machine
runs both fronts in an ordinary window and needs none of this.

Output names used to be a guess: sysfs calls the connectors `HDMI-A-1`/`HDMI-A-2`
while the X modesetting driver usually shortens them to `HDMI-1`/`HDMI-2`. That
guess failed silently on a kernel that disagreed, leaving both panels lit. Now
the names are read from `xrandr --query`, and the convention is only the last
resort: env var -> output actually present in X -> convention.

The exit code of `xrandr` says the command was accepted, not that the CRTC ended
up as asked, so activate() re-reads the state afterwards and only then reports
success.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)

LCD_OUTPUT_ENV = "CALC_LCD_XRANDR_OUTPUT"
MONITOR_OUTPUT_ENV = "CALC_MONITOR_XRANDR_OUTPUT"

# xrandr can hang if the X server is wedged; the UI must not hang with it.
_TIMEOUT_S = 10

# An output is *active* when xrandr prints a mode with an offset for it
# (`1920x1080+0+0`). "connected" only means a cable is in - a connected output
# with no CRTC is exactly the panel we are trying to switch off.
_ACTIVE_GEOMETRY = re.compile(r"\b\d+x\d+\+\d+\+\d+\b")


def drm_to_xrandr(connector: str) -> str:
    """`HDMI-A-1` (sysfs) -> `HDMI-1` (X modesetting driver)."""
    return connector.replace("-A-", "-")


def _normalized(name: str) -> str:
    """Comparison key that ignores how a port happens to be spelled.

    `HDMI-A-2`, `HDMI-2`, `HDMI2` and `hdmi-2` are one physical port written
    four ways; matching a DRM connector to an X output must not depend on which
    one this kernel/driver pair uses.
    """
    return drm_to_xrandr(name).replace("-", "").lower()


def available() -> bool:
    """True when there is an X display and an xrandr to talk to it."""
    return bool(os.environ.get("DISPLAY")) and shutil.which("xrandr") is not None


def missing_xrandr_on_x() -> bool:
    """An X server is running but the xrandr client is not installed.

    The two ways of being unavailable are not equally interesting. No DISPLAY
    is a developer machine doing exactly what it should. An X server with no
    xrandr binary is a broken image: every reconfiguration silently does
    nothing and both panels stay lit - precisely the failure this module exists
    to prevent - so that one has to be loud.
    """
    return bool(os.environ.get("DISPLAY")) and shutil.which("xrandr") is None


def read_outputs() -> dict[str, bool]:
    """Outputs the X server knows about, mapped to whether they are active.

    Returns an empty dict whenever the state cannot be read - no X server, no
    xrandr binary, a timeout, an error, or output in a shape this parser does
    not recognise. Callers read "empty" as "unknown", never as "no outputs", so
    a parsing surprise degrades to best effort instead of raising.

    `--query` rather than `--listmonitors`: the latter lists only *active*
    monitors, so it would never show the output we are trying to turn on.
    """
    if missing_xrandr_on_x():
        logger.warning("WRN-012 xrandr nao instalado; nao ha como ler as saidas do X")
        return {}

    if not available():
        return {}

    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            check=True,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("nao foi possivel ler as saidas do xrandr: %s", exc)
        return {}

    outputs: dict[str, bool] = {}
    for line in (proc.stdout or "").splitlines():
        # Mode lines are indented; output lines start at column 0, and
        # "Screen 0:" is the header rather than an output.
        if not line or line[0].isspace():
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] not in {"connected", "disconnected"}:
            continue
        outputs[parts[0]] = bool(_ACTIVE_GEOMETRY.search(line))

    if not outputs:
        logger.warning("saida do xrandr --query em formato inesperado")
    return outputs


def output_name(connector: str, env_var: str, outputs: dict[str, bool] | None = None) -> str:
    """The name `xrandr` uses for the port that sysfs calls `connector`.

    Precedence (D2): the env var wins, so bring-up can force a name without a
    new build; then an output actually present in X, matched regardless of
    spelling; then the convention, which is all a machine without X can offer.
    """
    override = os.environ.get(env_var)
    if override:
        return override

    if outputs is None:
        outputs = read_outputs()

    wanted = _normalized(connector)
    for name in outputs:
        if _normalized(name) == wanted:
            return name

    return drm_to_xrandr(connector)


def layout_matches(
    target: str, disable: tuple[str, ...] = (), outputs: dict[str, bool] | None = None
) -> bool | None:
    """Is `target` already the only active output?

    True/False when the state is readable, None when it is not. An unreadable
    state is not evidence of a wrong layout, and the two must not be conflated:
    None skips the idempotence shortcut without ever blocking startup.
    """
    if outputs is None:
        outputs = read_outputs()

    if not outputs or target not in outputs:
        return None

    if not outputs[target]:
        return False

    return not any(outputs.get(other, False) for other in disable if other != target)


def activate(target: str, disable: tuple[str, ...] = (), mode: str | None = None) -> bool:
    """Turn `target` on at its preferred mode and the others off.

    One xrandr call, so the server reconfigures once instead of blanking
    between two commands. Skipped entirely when the layout is already right,
    which stops the boot-time call and the per-front call from re-flashing the
    screen for nothing.

    Returns False when xrandr is unavailable, refused the change, or the
    re-read did not confirm the layout. Failures are logged as WRN-012 (PRD
    §13, reused) and never raise: the calculator has to come up either way
    (RF-04/RF-08).
    """
    others = tuple(other for other in disable if other != target)

    if missing_xrandr_on_x():
        _warn_layout(mode, target, others, "xrandr nao instalado (pacote ausente na imagem)")
        return False

    if not available():
        logger.debug("xrandr indisponivel; nao reconfigurando as saidas")
        return False

    if layout_matches(target, others) is True:
        logger.info(
            "layout de video ja correto: modo=%s alvo=%s desligadas=%s",
            mode,
            target,
            ",".join(others) or "-",
        )
        return True

    argv = ["xrandr", "--output", target, "--auto", "--primary"]
    for other in others:
        argv += ["--output", other, "--off"]

    try:
        subprocess.run(argv, check=True, capture_output=True, timeout=_TIMEOUT_S)
    except (subprocess.SubprocessError, OSError) as exc:
        _warn_layout(mode, target, others, f"xrandr falhou: {exc}")
        return False

    # The exit code says the command was accepted, not that the CRTC changed.
    verified = layout_matches(target, others)
    if verified is None:
        _warn_layout(mode, target, others, "estado das saidas nao verificavel")
        return False
    if not verified:
        _warn_layout(mode, target, others, "xrandr aceitou mas o layout nao mudou")
        return False

    logger.info(
        "layout de video aplicado e verificado: modo=%s alvo=%s desligadas=%s",
        mode,
        target,
        ",".join(others) or "-",
    )
    return True


def _warn_layout(mode: str | None, target: str, others: tuple[str, ...], reason: str) -> None:
    """WRN-012 (PRD §13): video state change or temporary absence.

    Reused rather than adding a code, and deliberately log-only: the spoken
    WRN-012 belongs to RF-09's *successful* screen swap, and saying the same
    sentence for a failure would give one phrase two opposite meanings.
    """
    logger.warning(
        "WRN-012 layout de video nao aplicado: modo=%s alvo=%s desligadas=%s (%s)",
        mode,
        target,
        ",".join(others) or "-",
        reason,
    )
