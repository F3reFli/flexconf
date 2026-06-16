from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flexconf import environment
from flexconf.environment import Environment, detect_environment


class DetectEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_which = environment.shutil.which

    def tearDown(self) -> None:
        environment.shutil.which = self._orig_which

    def _patch_which(self, available: set[str]) -> None:
        environment.shutil.which = lambda name: name if name in available else None

    def test_ready_when_all_required_present(self) -> None:
        self._patch_which({"dconf", "gsettings", "gnome-extensions"})
        env = detect_environment()
        self.assertTrue(env.is_ready)
        self.assertEqual(env.missing_required, ())
        self.assertEqual(env.missing_optional, ())

    def test_not_ready_when_required_missing(self) -> None:
        self._patch_which({"gsettings"})
        env = detect_environment()
        self.assertFalse(env.is_ready)
        self.assertIn("dconf", env.missing_required)
        self.assertIn("dconf", env.summary())

    def test_optional_missing_surfaces_as_warning(self) -> None:
        self._patch_which({"dconf", "gsettings"})
        env = detect_environment()
        self.assertTrue(env.is_ready)
        self.assertIn("gnome-extensions", env.missing_optional)
        self.assertTrue(any("optionnel" in w for w in env.warnings()))


class EnvironmentSummaryTests(unittest.TestCase):
    def test_non_gnome_desktop_warns_when_ready(self) -> None:
        env = Environment(
            missing_required=(),
            missing_optional=(),
            desktop="KDE",
            session_type="wayland",
            is_gnome=False,
        )
        self.assertTrue(env.is_ready)
        self.assertTrue(any("non-GNOME" in w for w in env.warnings()))

    def test_summary_reports_desktop_when_ready(self) -> None:
        env = Environment(
            missing_required=(),
            missing_optional=(),
            desktop="ubuntu:GNOME",
            session_type="wayland",
            is_gnome=True,
        )
        self.assertIn("ubuntu:GNOME", env.summary())
        self.assertIn("wayland", env.summary())


if __name__ == "__main__":
    unittest.main()
