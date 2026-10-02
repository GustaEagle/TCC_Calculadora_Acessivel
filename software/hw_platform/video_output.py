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

Orientation lives here too: the LCD is mounted upside down in the enclosure, so
its image has to be turned 180 graus, and only its own - the external monitor
stays upright. That makes rotation a property of the panel being lit, applied by
the same call that lights it.
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

# Rotacao de cada painel. O LCD e' montado de cabeca para baixo no gabinete, de
# modo que a imagem so' sai na posicao certa se o X a virar 180 graus - e apenas
# nele: o monitor externo fica em pe normal, e por isso a rotacao acompanha o
# painel alvo em vez de ser um ajuste global do ecra. As variaveis de ambiente
# seguem a mesma logica dos nomes de saida (PRD §11): a imagem pode ser corrigida
# num bring-up sem recompilar nada.
LCD_ROTATION_ENV = "CALC_LCD_ROTATE"
MONITOR_ROTATION_ENV = "CALC_MONITOR_ROTATE"
DEFAULT_LCD_ROTATION = "inverted"  # 180 graus: painel invertido no gabinete
DEFAULT_MONITOR_ROTATION = "normal"

# Vocabulario do `xrandr --rotate`. "inverted" e' o 180; "left"/"right" sao os 90
# que trocam largura por altura - nenhum deles e' usado pelo produto, mas ficam
# aceites para o caso de o painel ser remontado de lado.
ROTATIONS = ("normal", "left", "inverted", "right")

# Conveniencia de bring-up: CALC_LCD_ROTATE=180 diz o mesmo que "inverted" sem
# obrigar quem esta' na bancada a saber o vocabulario do xrandr.
_ROTATION_BY_DEGREES = {"0": "normal", "90": "left", "180": "inverted", "270": "right"}

# Uma saida rodada imprime a palavra depois da geometria ("800x480+0+0 inverted");
# "normal" nao e' impressa de todo. As mesmas palavras aparecem SEMPRE dentro dos
# parenteses, onde listam as rotacoes que a saida suporta - dai o parser cortar a
# linha no "(" antes de procurar.
_TURNED = ("left", "inverted", "right")

# xrandr can hang if the X server is wedged; the UI must not hang with it.
_TIMEOUT_S = 10

# An output is *active* when xrandr prints a mode with an offset for it
# (`1920x1080+0+0`). "connected" only means a cable is in - a connected output
# with no CRTC is exactly the panel we are trying to switch off.
_ACTIVE_GEOMETRY = re.compile(r"\b\d+x\d+\+\d+\+\d+\b")
# Cabecalho do `xrandr --query`: "Screen 0: minimum ..., current 1920 x 1080, ...".
_SCREEN_CURRENT = re.compile(r"\bcurrent\s+(\d+)\s*x\s*(\d+)")


def screen_size() -> tuple[int, int] | None:
    """Current X screen size according to xrandr, or None when unknown.

    Tk's winfo_screenwidth()/winfo_screenheight() come from Xlib's `Screen`
    struct, which is filled when the display connection is opened and is NOT
    refreshed when RandR resizes the screen. That is fine at boot and wrong in
    the case that matters: the external monitor is always plugged in with the
    calculator already running (RF-09), so the HDMI front is built moments
    after xrandr switched panels - and Tk would still report the 800x480 of the
    LCD, sizing the window (and choosing the layout tier) for the wrong panel.

    Asking xrandr avoids the cache entirely. Returns None off the Pi (no X, no
    xrandr, unparseable output), where the caller falls back to Tk.
    """
    if not available():
        return None

    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            check=True,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("nao foi possivel ler o tamanho da tela do xrandr: %s", exc)
        return None

    match = _SCREEN_CURRENT.search(proc.stdout or "")
    if match is None:
        logger.warning("cabecalho 'Screen ... current WxH' ausente na saida do xrandr")
        return None

    width, height = int(match.group(1)), int(match.group(2))
    if width < 1 or height < 1:
        return None
    return width, height


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


def _read_state() -> dict[str, tuple[bool, str]]:
    """Every output X knows about, as (active, rotation).

    The shared parse behind read_outputs() and read_rotations(): both answers
    come from the same `xrandr --query` line, so they are extracted once and the
    two public readers only choose which half they want.

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

    state: dict[str, tuple[bool, str]] = {}
    for line in (proc.stdout or "").splitlines():
        # Mode lines are indented; output lines start at column 0, and
        # "Screen 0:" is the header rather than an output.
        if not line or line[0].isspace():
            continue
        # Everything we read - name, status, geometry, rotation - comes before
        # the parenthesised list of rotations the output SUPPORTS; reading past
        # the "(" would find "inverted" on every output, rotated or not.
        head = line.split("(", 1)[0]
        parts = head.split()
        if len(parts) < 2 or parts[1] not in {"connected", "disconnected"}:
            continue
        rotation = next((part for part in parts[2:] if part in _TURNED), "normal")
        state[parts[0]] = (bool(_ACTIVE_GEOMETRY.search(head)), rotation)

    if not state:
        logger.warning("saida do xrandr --query em formato inesperado")
    return state


def read_outputs() -> dict[str, bool]:
    """Outputs the X server knows about, mapped to whether they are active."""
    return {name: active for name, (active, _rotation) in _read_state().items()}


def read_rotations() -> dict[str, str]:
    """Outputs the X server knows about, mapped to how they are rotated.

    One of ROTATIONS per output, "normal" included - xrandr prints nothing for
    an unrotated output, and "no word" is an answer, not a missing one. Empty
    dict when the state cannot be read, with the same meaning as read_outputs().
    """
    return {name: rotation for name, (_active, rotation) in _read_state().items()}


def rotation(env_var: str, default: str) -> str:
    """How the panel behind `env_var` should be rotated.

    Same precedence as output_name(), for the same reason: a panel remounted in
    the enclosure (or a second LCD that arrives the other way up) is corrected by
    an env var in the image, not by a code change. Degrees are accepted because
    the value is typed on a bench, not by someone reading this module; anything
    else falls back to the default rather than reaching the xrandr argv, where a
    typo would fail the whole call and leave the layout untouched.
    """
    raw = (os.environ.get(env_var) or "").strip().lower()
    if not raw:
        return default

    value = _ROTATION_BY_DEGREES.get(raw, raw)
    if value not in ROTATIONS:
        logger.warning(
            "%s=%r nao e uma rotacao valida (%s ou 0/90/180/270); usando %s",
            env_var,
            raw,
            "/".join(ROTATIONS),
            default,
        )
        return default
    return value


def rotation_matches(
    target: str, rotate: str, rotations: dict[str, str] | None = None
) -> bool | None:
    """Is `target` already rotated the way we want?

    True/False when the state is readable, None when it is not - the same
    three-valued answer as layout_matches(), and for the same reason: not
    knowing must not be mistaken for knowing it is wrong.
    """
    if rotations is None:
        rotations = read_rotations()

    if not rotations or target not in rotations:
        return None

    return rotations[target] == rotate


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


def activate(
    target: str,
    disable: tuple[str, ...] = (),
    mode: str | None = None,
    rotate: str = "normal",
) -> bool:
    """Turn `target` on at its preferred mode, rotated as asked, others off.

    One xrandr call, so the server reconfigures once instead of blanking
    between two commands. Skipped entirely when the layout is already right,
    which stops the boot-time call and the per-front call from re-flashing the
    screen for nothing.

    `rotate` is part of the layout, not a separate step: the LCD is mounted
    upside down in the enclosure and needs its 180 graus, while the external
    monitor must stay upright, so the rotation belongs to the panel being lit.
    It is always written to the argv, including "normal" - an output keeps
    whatever rotation it was last given, so only saying it explicitly makes the
    panel's orientation a consequence of this call rather than of its history.

    Returns False when xrandr is unavailable, refused the change, or the
    re-read did not confirm the layout. Failures are logged as WRN-012 (PRD
    §13, reused) and never raise: the calculator has to come up either way
    (RF-04/RF-08).
    """
    others = tuple(other for other in disable if other != target)

    if rotate not in ROTATIONS:
        # Never reaches the argv: xrandr would reject the whole command and the
        # panel that should have been lit would stay dark over a typo.
        logger.warning("rotacao %r desconhecida; usando normal", rotate)
        rotate = "normal"

    if missing_xrandr_on_x():
        _warn_layout(mode, target, others, "xrandr nao instalado (pacote ausente na imagem)")
        return False

    if not available():
        logger.debug("xrandr indisponivel; nao reconfigurando as saidas")
        return False

    if layout_matches(target, others) is True and rotation_matches(target, rotate) is True:
        logger.info(
            "layout de video ja correto: modo=%s alvo=%s rotacao=%s desligadas=%s",
            mode,
            target,
            rotate,
            ",".join(others) or "-",
        )
        return True

    argv = ["xrandr", "--output", target, "--auto", "--primary", "--rotate", rotate]
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

    # Same reasoning one step further: the panel can be lit and still be the
    # wrong way up, and an upside-down LCD is exactly as unusable as a dark one.
    rotated = rotation_matches(target, rotate)
    if rotated is None:
        _warn_layout(mode, target, others, f"rotacao de {target} nao verificavel")
        return False
    if not rotated:
        _warn_layout(
            mode, target, others, f"xrandr aceitou mas {target} nao ficou em '{rotate}'"
        )
        return False

    logger.info(
        "layout de video aplicado e verificado: modo=%s alvo=%s rotacao=%s desligadas=%s",
        mode,
        target,
        rotate,
        ",".join(others) or "-",
    )
    return True


def all_off(outputs: tuple[str, ...], mode: str | None = None) -> bool:
    """Switch every video output off: the user's blackout command.

    `outputs` are the panels' names as resolved by output_name(). Names X does
    not know are dropped - with only the LCD attached there is no monitor to
    switch off, and that is still a success - while any other output X reports
    as active is switched off too, because "screens off" means nothing lit.

    One xrandr call for all of them, for the same reason as activate(); then a
    re-read, and success only when no output is left active. `--off` releases
    the CRTC but leaves the connector `connected` in sysfs, so the RF-09 watcher
    does not mistake a blackout for a monitor being unplugged.

    Failures are logged as WRN-013 and never raise (RF-04/RF-08).
    """
    if missing_xrandr_on_x():
        _warn_blackout(mode, outputs, "xrandr nao instalado (pacote ausente na imagem)")
        return False

    if not available():
        _warn_blackout(mode, outputs, "sem servidor X ou sem xrandr")
        return False

    current = read_outputs()
    if not current:
        _warn_blackout(mode, outputs, "estado das saidas ilegivel")
        return False

    names = [name for name in dict.fromkeys(outputs) if name in current]
    names += [name for name, active in current.items() if active and name not in names]

    if not any(current[name] for name in names):
        logger.info("telas ja desligadas: modo=%s saidas=%s", mode, ",".join(names) or "-")
        return True

    argv = ["xrandr"]
    for name in names:
        argv += ["--output", name, "--off"]

    try:
        subprocess.run(argv, check=True, capture_output=True, timeout=_TIMEOUT_S)
    except (subprocess.SubprocessError, OSError) as exc:
        _warn_blackout(mode, tuple(names), f"xrandr falhou: {exc}")
        return False

    # The exit code says the command was accepted, not that the CRTCs let go.
    after = read_outputs()
    if not after:
        _warn_blackout(mode, tuple(names), "estado das saidas nao verificavel")
        return False
    still_active = [name for name, active in after.items() if active]
    if still_active:
        _warn_blackout(
            mode, tuple(names), f"xrandr aceitou mas continuam ativas: {','.join(still_active)}"
        )
        return False

    logger.info("telas desligadas e verificadas: modo=%s saidas=%s", mode, ",".join(names))
    return True


# Linha de modo sob uma saida do `xrandr --query`: "   1920x1080     60.00 +  50.00".
# O "+" depois de uma taxa marca o modo preferido; o "*", o modo em uso.
_MODE_LINE = re.compile(r"^\s+(\d+)x(\d+)\S*\s+(.*)$")


def preferred_size(output: str) -> tuple[int, int] | None:
    """Preferred mode of `output` according to xrandr, or None when unknown.

    What a front should size itself for while every CRTC is off: the screen X
    reports then is whatever is left without an active output (often its
    minimum), and sizing from it would pick the wrong layout tier for the panel
    that will relight. A connected output keeps listing its modes when off, so
    the answer is still there. Falls back to the first mode listed when none is
    marked preferred; None off the Pi or when `output` is not listed.
    """
    if not available():
        return None

    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            check=True,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("nao foi possivel ler os modos de %s no xrandr: %s", output, exc)
        return None

    in_block = False
    first: tuple[int, int] | None = None
    for line in (proc.stdout or "").splitlines():
        if line and not line[0].isspace():
            if in_block:
                break
            in_block = line.split(maxsplit=1)[0] == output
            continue
        if not in_block:
            continue
        match = _MODE_LINE.match(line)
        if match is None:
            continue
        size = int(match.group(1)), int(match.group(2))
        if "+" in match.group(3):
            return size
        first = first or size

    return first


def _warn_blackout(mode: str | None, outputs: tuple[str, ...], reason: str) -> None:
    """WRN-013 (PRD §13): screens switched off/on by the user's command.

    Its own code rather than WRN-012: a deliberate command is not the automatic
    swap of RF-09. The front speaks the matching WRN-013 sentence; this is the
    log side, which is all a bring-up without a console can read.
    """
    logger.warning(
        "WRN-013 telas nao desligadas: modo=%s saidas=%s (%s)",
        mode,
        ",".join(outputs) or "-",
        reason,
    )


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
