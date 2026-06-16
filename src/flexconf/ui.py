from __future__ import annotations

import curses
from dataclasses import dataclass

# Color pair identifiers. Kept as module constants so every screen draws
# with the same palette. Pair 0 is reserved by curses for the default.
PAIR_ACCENT = 1      # brand / titles / progress fill
PAIR_SELECT = 2      # highlighted menu row
PAIR_DIM = 3         # secondary text, borders
PAIR_SUCCESS = 4     # success status messages
PAIR_WARNING = 5     # warning status messages
PAIR_ERROR = 6       # error status messages
PAIR_LOGO = 7        # splash logo

# Braille spinner frames — smooth and lightweight.
SPINNER_FRAMES: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

# Box-drawing glyphs (rounded corners give a softer, modern look).
_TL, _TR, _BL, _BR = "╭", "╮", "╰", "╯"
_H, _V = "─", "│"


@dataclass(frozen=True)
class Status:
    """A status line plus the semantic color it should be rendered with."""

    text: str
    pair: int = PAIR_DIM

    @classmethod
    def info(cls, text: str) -> "Status":
        return cls(text, PAIR_DIM)

    @classmethod
    def success(cls, text: str) -> "Status":
        return cls(text, PAIR_SUCCESS)

    @classmethod
    def warning(cls, text: str) -> "Status":
        return cls(text, PAIR_WARNING)

    @classmethod
    def error(cls, text: str) -> "Status":
        return cls(text, PAIR_ERROR)


def init_colors() -> bool:
    """Initialise the FlexConf palette. Returns False if colors are unavailable.

    Uses ``use_default_colors`` so the terminal's own background shows through
    (works well with transparent/themed terminals like kitty).
    """
    if not curses.has_colors():
        return False
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK

    curses.init_pair(PAIR_ACCENT, curses.COLOR_CYAN, bg)
    curses.init_pair(PAIR_SELECT, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(PAIR_DIM, curses.COLOR_WHITE, bg)
    curses.init_pair(PAIR_SUCCESS, curses.COLOR_GREEN, bg)
    curses.init_pair(PAIR_WARNING, curses.COLOR_YELLOW, bg)
    curses.init_pair(PAIR_ERROR, curses.COLOR_RED, bg)
    curses.init_pair(PAIR_LOGO, curses.COLOR_MAGENTA, bg)
    return True


def color(pair: int) -> int:
    """Return the curses attribute for a color pair, or 0 if no color support."""
    if not curses.has_colors():
        return 0
    return curses.color_pair(pair)


def safe_addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    """addstr that never raises on the bottom-right cell or out-of-bounds writes."""
    height, width = win.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    # curses errors when writing the final cell of the window; clip to fit.
    text = text[: max(0, width - x - 1)]
    if not text:
        return
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def center_x(width: int, text: str) -> int:
    """Left column so *text* is horizontally centered in *width*."""
    return max(0, (width - _display_len(text)) // 2)


def draw_box(
    win,
    top: int,
    left: int,
    height: int,
    width: int,
    *,
    title: str = "",
    attr: int = 0,
) -> None:
    """Draw a rounded box with an optional centered title in the top border."""
    if height < 2 or width < 2:
        return
    bottom = top + height - 1
    right = left + width - 1

    safe_addstr(win, top, left, _TL + _H * (width - 2) + _TR, attr)
    safe_addstr(win, bottom, left, _BL + _H * (width - 2) + _BR, attr)
    for row in range(top + 1, bottom):
        safe_addstr(win, row, left, _V, attr)
        safe_addstr(win, row, right, _V, attr)

    if title:
        label = f" {title} "
        tx = left + center_x(width, label)
        safe_addstr(win, top, tx, label, attr | curses.A_BOLD)


def progress_bar(width: int, fraction: float) -> str:
    """Render a unicode progress bar of *width* cells for *fraction* in [0, 1]."""
    width = max(1, width)
    fraction = min(1.0, max(0.0, fraction))
    filled = int(round(fraction * width))
    return "█" * filled + "░" * (width - filled)


def _display_len(text: str) -> int:
    """Length of *text* as drawn. Plain count is fine for our glyph set."""
    return len(text)
