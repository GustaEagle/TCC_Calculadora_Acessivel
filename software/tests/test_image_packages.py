"""The image has to ship the tools the app shells out to.

Regression from the hardware bring-up: `xorg-server` and `xinit` were installed
but `xrandr` was not - it is a separate apk - so every attempt to apply the
exclusive video layout was a no-op and both panels stayed lit (PRD §7.2). The
Python side had tests, the package list did not.
"""

import pathlib
import unittest

PACKAGES = (
    pathlib.Path(__file__).resolve().parents[2]
    / "system" / "rpi-os" / "alpine" / "packages"
)


def installed_packages() -> set[str]:
    """Mirror of the parser in build-alpine-img.sh: first word, no comments."""
    names = set()
    for line in PACKAGES.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        names.add(stripped.split()[0])
    return names


class ImagePackagesTest(unittest.TestCase):
    def test_the_package_list_exists(self) -> None:
        self.assertTrue(PACKAGES.is_file(), f"nao achei {PACKAGES}")

    def test_xrandr_is_installed(self) -> None:
        """Without it video_output cannot switch a panel off at all."""
        self.assertIn(
            "xrandr",
            installed_packages(),
            "o pacote 'xrandr' e obrigatorio: sem ele a saida exclusiva do "
            "PRD §7.2 nunca e aplicada e as duas telas ficam acesas",
        )

    def test_the_x_tools_the_kiosk_session_calls_are_installed(self) -> None:
        """Everything .xinitrc invokes has to exist in the rootfs."""
        for package in ("xorg-server", "xinit", "xset", "xrandr"):
            self.assertIn(package, installed_packages())

    def test_comment_only_lines_are_not_read_as_packages(self) -> None:
        """The build strips them, so this parser must strip them too."""
        self.assertFalse({name for name in installed_packages() if name.startswith("#")})


if __name__ == "__main__":
    unittest.main()
