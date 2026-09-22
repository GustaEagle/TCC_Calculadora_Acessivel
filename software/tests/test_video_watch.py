"""RF-09: the front follows the video output without a manual restart.

The monitor is always connected with the calculator already running (the LCD
is inside the enclosure and is there at boot), so this is the normal flow, not
an edge case.
"""

import unittest

from software.hw_platform.display import (
    DisplayMode,
    DisplaySelector,
    DisplayWatcher,
    SimulatedHdmiPortReader,
)
from software.ui.shared.video_watch import VideoOutputWatch, video_changed_speech


class FakeRoot:
    """Stand-in for the Tk window: records after() instead of scheduling it."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[int, object]] = []
        self.destroyed = False

    def after(self, delay_ms: int, callback) -> None:
        self.scheduled.append((delay_ms, callback))

    def destroy(self) -> None:
        self.destroyed = True

    def run_pending(self) -> None:
        """Fire everything queued so far, once."""
        pending, self.scheduled = self.scheduled, []
        for _delay, callback in pending:
            callback()


class FakeSpeech:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def interrupt_and_say(self, text: str) -> None:
        self.spoken.append(text)


class DisplayWatcherTest(unittest.TestCase):
    def test_poll_returns_none_while_the_output_is_unchanged(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=False)
        watcher = DisplayWatcher(DisplaySelector(reader))
        self.assertIsNone(watcher.poll())
        self.assertIsNone(watcher.poll())

    def test_poll_reports_a_monitor_plugged_in_while_running(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=False)
        watcher = DisplayWatcher(DisplaySelector(reader))

        reader.monitor_present = True
        self.assertEqual(watcher.poll(), DisplayMode.HDMI)

    def test_a_change_is_reported_once(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=False)
        watcher = DisplayWatcher(DisplaySelector(reader))

        reader.monitor_present = True
        watcher.poll()
        self.assertIsNone(watcher.poll())

    def test_poll_reports_the_monitor_being_unplugged(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=True)
        watcher = DisplayWatcher(DisplaySelector(reader))

        reader.monitor_present = False
        self.assertEqual(watcher.poll(), DisplayMode.LCD)

    def test_starting_mode_can_be_given_instead_of_probed(self) -> None:
        reader = SimulatedHdmiPortReader(monitor_present=True)
        watcher = DisplayWatcher(DisplaySelector(reader), mode=DisplayMode.LCD)
        self.assertEqual(watcher.poll(), DisplayMode.HDMI)


class VideoOutputWatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = FakeRoot()
        self.speech = FakeSpeech()
        self.reader = SimulatedHdmiPortReader(monitor_present=False)
        self.watch = VideoOutputWatch(
            self.root,
            self.speech,
            DisplayMode.LCD,
            watcher=DisplayWatcher(DisplaySelector(self.reader), mode=DisplayMode.LCD),
        )

    def test_keeps_polling_and_stays_quiet_while_nothing_changes(self) -> None:
        self.watch.start()
        for _ in range(3):
            self.root.run_pending()

        self.assertFalse(self.root.destroyed)
        self.assertEqual(self.speech.spoken, [])
        self.assertIsNone(self.watch.changed_to)

    def test_plugging_the_monitor_closes_the_front_and_names_the_successor(self) -> None:
        self.watch.start()
        self.reader.monitor_present = True
        self.root.run_pending()  # poll notices the change

        self.assertEqual(self.watch.changed_to, DisplayMode.HDMI)
        self.assertTrue(self.root.destroyed)

    def test_the_warning_is_announced_on_the_way_out(self) -> None:
        self.watch.start()
        self.reader.monitor_present = True
        self.root.run_pending()

        self.assertEqual(len(self.speech.spoken), 1)
        self.assertIn("Aviso 012", self.speech.spoken[0])

    def test_polling_stops_once_a_change_was_seen(self) -> None:
        self.watch.start()
        self.reader.monitor_present = True
        self.root.run_pending()

        # Nothing is rescheduled: the window is gone and the entry point takes
        # over from here.
        self.assertEqual(self.root.scheduled, [])

    def test_speech_names_the_panel_taking_over(self) -> None:
        """PRD §13 WRN-012 (P2): the user may not be looking at any screen."""
        for mode in DisplayMode:
            with self.subTest(mode=mode):
                spoken = video_changed_speech(mode)
                self.assertIn("Aviso 012", spoken)
                self.assertIn("Saida de video alterada", spoken)


if __name__ == "__main__":
    unittest.main()
