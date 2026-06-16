from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flexconf import ui
from flexconf.ui import Status


class ProgressBarTests(unittest.TestCase):
    def test_empty(self) -> None:
        bar = ui.progress_bar(10, 0.0)
        self.assertEqual(bar, "░" * 10)

    def test_full(self) -> None:
        bar = ui.progress_bar(10, 1.0)
        self.assertEqual(bar, "█" * 10)

    def test_half_keeps_width(self) -> None:
        bar = ui.progress_bar(10, 0.5)
        self.assertEqual(len(bar), 10)
        self.assertEqual(bar.count("█"), 5)

    def test_fraction_is_clamped(self) -> None:
        self.assertEqual(ui.progress_bar(8, -2.0), "░" * 8)
        self.assertEqual(ui.progress_bar(8, 5.0), "█" * 8)


class CenterTests(unittest.TestCase):
    def test_centers_text(self) -> None:
        self.assertEqual(ui.center_x(10, "abcd"), 3)

    def test_never_negative(self) -> None:
        self.assertEqual(ui.center_x(2, "too-long-text"), 0)


class StatusTests(unittest.TestCase):
    def test_semantic_factories_use_distinct_pairs(self) -> None:
        pairs = {
            Status.info("a").pair,
            Status.success("b").pair,
            Status.warning("c").pair,
            Status.error("d").pair,
        }
        self.assertEqual(len(pairs), 4)

    def test_status_is_immutable(self) -> None:
        status = Status.success("done")
        with self.assertRaises(Exception):
            status.text = "changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
