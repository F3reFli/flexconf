from __future__ import annotations

import curses
import time
from collections.abc import Callable
from dataclasses import dataclass

from flexconf import ui

# Big block logo (used when the terminal is wide enough), plus a compact
# fallback for narrow windows.
_LOGO_BIG: tuple[str, ...] = (
    "███████╗██╗     ███████╗██╗  ██╗ ██████╗ ██████╗ ███╗   ██╗███████╗",
    "██╔════╝██║     ██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗████╗  ██║██╔════╝",
    "█████╗  ██║     █████╗   ╚███╔╝ ██║     ██║   ██║██╔██╗ ██║█████╗  ",
    "██╔══╝  ██║     ██╔══╝   ██╔██╗ ██║     ██║   ██║██║╚██╗██║██╔══╝  ",
    "██║     ███████╗███████╗██╔╝ ██╗╚██████╗╚██████╔╝██║ ╚████║██║     ",
    "╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ",
)
_LOGO_SMALL: tuple[str, ...] = ("┌─┐┬  ┌─┐─┐ ┬┌─┐┌─┐┌┐┌┌─┐", "├┤ │  ├┤ ┌┴┬┘│  │ │││││├┤ ", "└  ┴─┘└─┘┴ └─└─┘└─┘┘└┘└  ")

_TAGLINE = "Snapshot & restore your Ubuntu desktop"
_FRAME_SECONDS = 0.06  # ~16 fps animation


@dataclass(frozen=True)
class LoadStep:
    """A labelled unit of startup work animated on the splash screen."""

    label: str
    action: Callable[[], object]


def run_splash(
    stdscr: "curses._CursesWindow",
    steps: list[LoadStep],
    *,
    min_duration: float = 1.4,
) -> list[object]:
    """Animate the loading screen while executing *steps*.

    Each step's ``action`` is run once; its return value is collected and
    returned in order. The screen shows a logo, a spinner and a progress bar.
    A minimum duration keeps fast machines from flashing the splash. Any
    keypress skips the remaining animation (work still completes).
    """
    stdscr.nodelay(True)
    results: list[object] = []
    total = max(1, len(steps))
    per_step = max(0.0, min_duration) / total
    skipped = False

    spinner_index = 0
    for position, step in enumerate(steps):
        result = step.action()
        results.append(result)

        target = (position + 1) / total
        start = position / total
        if skipped:
            continue

        deadline = time.monotonic() + per_step
        while time.monotonic() < deadline:
            elapsed = 1.0 - max(0.0, (deadline - time.monotonic()) / per_step)
            fraction = start + (target - start) * elapsed
            spinner_index = (spinner_index + 1) % len(ui.SPINNER_FRAMES)
            _draw(stdscr, step.label, fraction, spinner_index)
            if stdscr.getch() != -1:
                skipped = True
                break
            time.sleep(_FRAME_SECONDS)

    if not skipped:
        _draw(stdscr, "Prêt.", 1.0, spinner_index)
        time.sleep(0.25)

    stdscr.nodelay(False)
    return results


def _draw(
    stdscr: "curses._CursesWindow",
    label: str,
    fraction: float,
    spinner_index: int,
) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    logo = _LOGO_BIG if width >= len(_LOGO_BIG[0]) + 4 else _LOGO_SMALL
    block_height = len(logo) + 6
    top = max(0, (height - block_height) // 2)

    logo_attr = ui.color(ui.PAIR_LOGO) | curses.A_BOLD
    for offset, line in enumerate(logo):
        ui.safe_addstr(stdscr, top + offset, ui.center_x(width, line), line, logo_attr)

    tag_row = top + len(logo) + 1
    ui.safe_addstr(
        stdscr,
        tag_row,
        ui.center_x(width, _TAGLINE),
        _TAGLINE,
        ui.color(ui.PAIR_DIM),
    )

    bar_width = min(40, max(10, width - 10))
    bar = ui.progress_bar(bar_width, fraction)
    percent = f"{int(round(fraction * 100)):3d}%"
    bar_text = f"{bar} {percent}"
    ui.safe_addstr(
        stdscr,
        tag_row + 2,
        ui.center_x(width, bar_text),
        bar_text,
        ui.color(ui.PAIR_ACCENT),
    )

    spinner = ui.SPINNER_FRAMES[spinner_index % len(ui.SPINNER_FRAMES)]
    status = f"{spinner}  {label}"
    ui.safe_addstr(
        stdscr,
        tag_row + 3,
        ui.center_x(width, status),
        status,
        ui.color(ui.PAIR_DIM),
    )

    hint = "(une touche pour passer)"
    ui.safe_addstr(stdscr, height - 1, ui.center_x(width, hint), hint, ui.color(ui.PAIR_DIM) | curses.A_DIM)
    stdscr.refresh()
