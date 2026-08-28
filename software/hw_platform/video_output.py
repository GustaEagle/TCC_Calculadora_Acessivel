"""Point the X server at the panel that should show the UI.

Detecting the change (display.py) is only half of it: X keeps driving whatever
output it configured at startup, so a monitor plugged in later stays dark until
someone enables it. `xrandr` does that without restarting the X server, which
is what lets the swap happen with the calculator still running.

Everything here is best effort. Off the Pi there is no X server and no xrandr,
and the calls simply report failure instead of raising — a developer machine
runs both fronts in an ordinary window and needs none of this.

The output names are the last loose end: sysfs calls the connectors
`HDMI-A-1`/`HDMI-A-2` while the X modesetting driver usually shortens them to
`HDMI-1`/`HDMI-2`. drm_to_xrandr() applies that convention, and the env vars
override it if this kernel/driver pair disagrees.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

LCD_OUTPUT_ENV = "CALC_LCD_XRANDR_OUTPUT"
MONITOR_OUTPUT_ENV = "CALC_MONITOR_XRANDR_OUTPUT"

# xrandr can hang if the X server is wedged; the UI must not hang with it.
_TIMEOUT_S = 10


def drm_to_xrandr(connector: str) -> str:
    """`HDMI-A-1` (sysfs) -> `HDMI-1` (X modesetting driver)."""
    return connector.replace("-A-", "-")


def output_name(connector: str, env_var: str) -> str:
    return os.environ.get(env_var) or drm_to_xrandr(connector)


def available() -> bool:
    """True when there is an X display and an xrandr to talk to it."""
    return bool(os.environ.get("DISPLAY")) and shutil.which("xrandr") is not None


def activate(target: str, disable: tuple[str, ...] = ()) -> bool:
    """Turn `target` on at its preferred mode and the others off.

    One xrandr call, so the server reconfigures once instead of blanking
    between two commands. Returns False when xrandr is unavailable or refused
    the change — the caller carries on either way, since the window may well
    land on the right panel without help.
    """
    if not available():
        logger.debug("xrandr indisponivel; nao reconfigurando as saidas")
        return False

    argv = ["xrandr", "--output", target, "--auto", "--primary"]
    for other in disable:
        if other != target:
            argv += ["--output", other, "--off"]

    try:
        subprocess.run(argv, check=True, capture_output=True, timeout=_TIMEOUT_S)
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("xrandr falhou ao ativar %s: %s", target, exc)
        return False

    logger.info("saida de video ativa: %s", target)
    return True
