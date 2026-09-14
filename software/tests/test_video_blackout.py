"""video-blackout: the screens go dark by command, and the way back is spoken.

Everything here runs without DISPLAY and without Tk: the applier that would
talk to xrandr is replaced by a double that records its calls.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from software.hw_platform.display import DisplayMode
from software.ui.shared import video_blackout
from software.ui.shared.video_blackout import (
    RELIGHT_KEY_NAME,
    VideoBlackout,
    relight_on_ac,
    toggle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class FakeApplier:
    """Records whether the blackout was on at each call; answers `result`."""

    def __init__(self, result=DisplayMode.LCD) -> None:
        self.result = result
        self.calls: list[bool] = []
        self.session: VideoBlackout | None = None

    def __call__(self):
        self.calls.append(self.session.active if self.session else None)
        return self.result


def bound(session: VideoBlackout, result=DisplayMode.LCD) -> FakeApplier:
    applier = FakeApplier(result)
    applier.session = session
    return applier


class SessionStateTest(unittest.TestCase):
    """2.1"""

    def test_a_session_starts_lit(self) -> None:
        """No boot may present itself as a device without an image."""
        self.assertFalse(VideoBlackout().active)

    def test_the_module_imports_without_tk(self) -> None:
        """Importable where there is no display: the audio path and the CI."""
        code = (
            "import sys, software.ui.shared.video_blackout; "
            "sys.exit(1 if 'tkinter' in sys.modules else 0)"
        )
        env = {key: value for key, value in os.environ.items() if key != "DISPLAY"}
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


class SpeechTest(unittest.TestCase):
    """2.2: WRN-013, never WRN-012."""

    def test_the_blackout_sentence_names_the_key_that_undoes_it(self) -> None:
        """AC alone relights, and it is the same key on the PC (Esc)."""
        spoken = video_blackout.blackout_speech()
        self.assertTrue(spoken.startswith("Aviso 013."))
        self.assertEqual(RELIGHT_KEY_NAME, "AC")
        self.assertIn(RELIGHT_KEY_NAME, spoken)

    def test_the_relit_sentence_names_the_panel(self) -> None:
        self.assertIn("monitor", video_blackout.relit_speech(DisplayMode.HDMI))
        self.assertIn("calculadora", video_blackout.relit_speech(DisplayMode.LCD))

    def test_every_sentence_is_warning_013(self) -> None:
        for spoken in (
            video_blackout.blackout_speech(),
            video_blackout.relit_speech(DisplayMode.LCD),
            video_blackout.blackout_failed_speech(),
            video_blackout.relight_failed_speech(),
        ):
            self.assertTrue(spoken.startswith("Aviso 013."), spoken)
            self.assertNotIn("012", spoken)


class ToggleTest(unittest.TestCase):
    """2.3"""

    def test_switching_off_sets_the_flag_before_applying(self) -> None:
        """The applier reads the flag: it must already say "off" when called."""
        session = VideoBlackout()
        applier = bound(session)

        spoken = toggle(session, applier)

        self.assertTrue(session.active)
        self.assertEqual(applier.calls, [True])
        self.assertEqual(spoken, video_blackout.blackout_speech())

    def test_switching_back_on_names_the_panel_that_relit(self) -> None:
        session = VideoBlackout(active=True)
        applier = bound(session, DisplayMode.HDMI)

        spoken = toggle(session, applier)

        self.assertFalse(session.active)
        self.assertEqual(applier.calls, [False])
        self.assertEqual(spoken, video_blackout.relit_speech(DisplayMode.HDMI))

    def test_a_failed_blackout_leaves_the_screen_lit_and_says_so(self) -> None:
        session = VideoBlackout()

        spoken = toggle(session, bound(session, None))

        self.assertFalse(session.active)
        self.assertEqual(spoken, video_blackout.blackout_failed_speech())

    def test_a_failed_relight_keeps_the_blackout_so_the_next_press_retries(self) -> None:
        session = VideoBlackout(active=True)

        spoken = toggle(session, bound(session, None))

        self.assertTrue(session.active)
        self.assertEqual(spoken, video_blackout.relight_failed_speech())


class RelightOnAcTest(unittest.TestCase):
    """2.4"""

    def test_ac_relights_a_dark_screen(self) -> None:
        session = VideoBlackout(active=True)
        applier = bound(session)

        spoken = relight_on_ac(session, applier)

        self.assertFalse(session.active)
        self.assertEqual(applier.calls, [False])
        self.assertEqual(spoken, video_blackout.relit_speech(DisplayMode.LCD))

    def test_ac_with_the_screen_lit_does_not_touch_the_video(self) -> None:
        session = VideoBlackout()
        applier = bound(session)

        self.assertIsNone(relight_on_ac(session, applier))
        self.assertEqual(applier.calls, [])
        self.assertFalse(session.active)


if __name__ == "__main__":
    unittest.main()
