"""VolumeController: ajusta o mixer ALSA via amixer, com limites e parsing."""

import subprocess
import unittest

from software.hw_platform.volume import VolumeController


class _FakeAmixer:
    """Simula o `amixer`: guarda o nível e devolve a saída no formato real."""

    def __init__(self, level: int = 50, *, fail: bool = False) -> None:
        self.level = level
        self.fail = fail
        self.calls: list[list[str]] = []

    def __call__(self, cmd, capture_output, text, check):
        self.calls.append(cmd)
        if self.fail:
            raise FileNotFoundError("amixer ausente")
        # cmd = [amixer, -M, set/get, Control, [NN%]]
        action = cmd[2]
        if action == "set":
            percent = int(cmd[4].rstrip("%"))
            self.level = max(0, min(100, percent))
        out = f"  Mono: Playback 128 [{self.level}%] [on]\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")


class VolumeControllerTest(unittest.TestCase):
    def test_current_parses_percentage(self) -> None:
        amixer = _FakeAmixer(level=37)
        vol = VolumeController(runner=amixer)
        self.assertEqual(vol.current(), 37)

    def test_increase_and_decrease_use_a_fixed_step(self) -> None:
        amixer = _FakeAmixer(level=50)
        vol = VolumeController(step=10, runner=amixer)
        self.assertEqual(vol.increase(), 60)
        self.assertEqual(vol.decrease(), 50)

    def test_does_not_exceed_maximum(self) -> None:
        amixer = _FakeAmixer(level=95)
        vol = VolumeController(step=10, runner=amixer)
        self.assertEqual(vol.increase(), 100)
        self.assertEqual(vol.increase(), 100)

    def test_does_not_drop_below_minimum(self) -> None:
        amixer = _FakeAmixer(level=5)
        vol = VolumeController(step=10, runner=amixer)
        self.assertEqual(vol.decrease(), 0)
        self.assertEqual(vol.decrease(), 0)

    def test_unavailable_mixer_returns_none(self) -> None:
        amixer = _FakeAmixer(fail=True)
        vol = VolumeController(runner=amixer)
        self.assertIsNone(vol.current())
        self.assertIsNone(vol.increase())
        self.assertIsNone(vol.decrease())

    def test_uses_mapped_scale_and_configured_control(self) -> None:
        amixer = _FakeAmixer(level=50)
        vol = VolumeController(control="PCM", runner=amixer)
        vol.increase()
        first = amixer.calls[0]
        self.assertIn("-M", first)       # escala mapeada (percepção linear)
        self.assertIn("PCM", first)      # controle configurável


if __name__ == "__main__":
    unittest.main()
