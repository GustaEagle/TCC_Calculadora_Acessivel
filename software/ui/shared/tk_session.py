"""Reset ttkbootstrap's process-global state between fronts (RF-09).

The handover destroys one root window and builds another in the SAME process,
which is what keeps the expression and the history alive across a screen swap.
ttkbootstrap does not expect that: it keeps the Style as a class-level
singleton and the Publisher's subscribers in a class-level dict, both bound to
the Tcl interpreter of the window that created them.

So the second front gets `Style.__new__` returning the stale instance and
`Style.__init__` returning early without building a single style - the window
comes up in Tk's default theme (`vista` on Windows, `default` on the Pi) with
none of the palette, and the dead interpreter raises "application has been
destroyed" on the way. Clearing both globals first makes the new window build
its theme from scratch, exactly as the first one did.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def reset_ttkbootstrap_globals() -> None:
    """Drop the Style singleton and subscribers left behind by a previous front.

    Call before creating the root window. Harmless before the first front:
    there is nothing to clear yet.

    Best effort - a future ttkbootstrap that reorganises these internals must
    not be the reason the calculator fails to come up, so problems here are
    logged and swallowed (WRN-012 territory: the UI still works, it just looks
    wrong).
    """
    try:
        from ttkbootstrap.publisher import Publisher
        from ttkbootstrap.style import Style
    except ImportError:  # pragma: no cover - only reachable without ttkbootstrap
        return

    try:
        if Style.instance is None:
            return

        Style.instance = None
        Publisher.clear_subscribers()
        logger.info("estado global do ttkbootstrap reiniciado para o novo front")
    except Exception:  # pragma: no cover - defensive, see docstring
        logger.warning(
            "nao foi possivel reiniciar o estado do ttkbootstrap; "
            "o novo front pode aparecer sem estilizacao",
            exc_info=True,
        )
