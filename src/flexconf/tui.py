from __future__ import annotations

import curses

from flexconf.manager import ThemeError, ThemeManager

_MENU_TOP = 3       # first row used for menu items
_FOOTER_ROWS = 3    # separator + message + 1 spare at bottom


class FlexConfTUI:
    def __init__(self, manager: ThemeManager) -> None:
        self.manager = manager
        self.status_message = "Pret."

    def run(self) -> None:
        curses.wrapper(self._main)

    def _main(self, stdscr: "curses._CursesWindow") -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # Some terminals don't support cursor visibility control
        stdscr.keypad(True)

        while True:
            choice = self._menu(
                stdscr,
                "FlexConf  [j/k ou fleches, Entree pour selectionner, q pour quitter]",
                ["Choisir theme", "Prendre snapshot", "Quitter"],
            )
            if choice == 0:
                self._choose_theme(stdscr)
            elif choice == 1:
                self._take_snapshot(stdscr)
            else:
                return

    def _choose_theme(self, stdscr: "curses._CursesWindow") -> None:
        themes = self.manager.list_themes()
        if not themes:
            self.status_message = "Aucun theme disponible dans themes/."
            return

        options = themes + ["Retour"]
        selected = self._menu(stdscr, "Choisir un theme", options)
        if selected == len(options) - 1:
            return

        theme_name = options[selected]
        try:
            result = self.manager.apply_theme(theme_name)
        except ThemeError as error:
            self.status_message = str(error)
            return
        self.status_message = result.format_message("Application")

    def _take_snapshot(self, stdscr: "curses._CursesWindow") -> None:
        snapshot_name = self._prompt(stdscr, "Nom du snapshot: ")
        if snapshot_name is None:
            self.status_message = "Snapshot annule."
            return

        try:
            result = self.manager.snapshot_theme(snapshot_name)
        except ThemeError as error:
            self.status_message = str(error)
            return
        self.status_message = result.format_message("Snapshot")

    def _menu(
        self,
        stdscr: "curses._CursesWindow",
        title: str,
        options: list[str],
    ) -> int:
        index = 0
        scroll = 0

        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()

            # Title on row 1
            if height > 1:
                safe_title = title[: max(1, width - 2)]
                title_x = max(0, (width - len(safe_title)) // 2)
                stdscr.addstr(1, title_x, safe_title, curses.A_BOLD)

            # Available rows for menu items
            max_visible = max(1, height - _MENU_TOP - _FOOTER_ROWS)

            # Keep selected item in the visible window
            if index < scroll:
                scroll = index
            elif index >= scroll + max_visible:
                scroll = index - max_visible + 1

            for slot in range(max_visible):
                opt_idx = scroll + slot
                if opt_idx >= len(options):
                    break
                y = _MENU_TOP + slot
                if y >= height - _FOOTER_ROWS:
                    break
                label = options[opt_idx][: max(1, width - 8)]
                prefix = "  "
                if opt_idx == index:
                    prefix = "> "
                mode = curses.A_REVERSE if opt_idx == index else curses.A_NORMAL
                stdscr.addstr(y, 2, prefix + label, mode)

            # Scroll indicators
            if scroll > 0 and height > _MENU_TOP:
                stdscr.addstr(_MENU_TOP, width - 4, " /\\")
            if scroll + max_visible < len(options) and height > _MENU_TOP + 1:
                stdscr.addstr(min(_MENU_TOP + max_visible, height - _FOOTER_ROWS - 1), width - 4, " \\/")

            self._draw_footer(stdscr, self.status_message)
            stdscr.refresh()

            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                index = (index - 1) % len(options)
            elif key in (curses.KEY_DOWN, ord("j")):
                index = (index + 1) % len(options)
            elif key in (curses.KEY_PPAGE,):   # Page Up
                index = max(0, index - max_visible)
            elif key in (curses.KEY_NPAGE,):   # Page Down
                index = min(len(options) - 1, index + max_visible)
            elif key in (10, 13, curses.KEY_ENTER):
                return index
            elif key in (27, ord("q")):
                return len(options) - 1

    def _prompt(
        self,
        stdscr: "curses._CursesWindow",
        prompt: str,
    ) -> str | None:
        curses.curs_set(1)
        curses.echo()
        try:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            if height > 1:
                stdscr.addstr(1, 2, prompt, curses.A_BOLD)
            if height > 2:
                stdscr.addstr(2, 2, "(vide + Entree pour annuler)")
            self._draw_footer(stdscr, "Entree pour valider.")
            stdscr.refresh()
            input_row = min(4, max(3, height - _FOOTER_ROWS - 1))
            raw = stdscr.getstr(input_row, 2, 60)
            value = raw.decode("utf-8", errors="replace").strip()
            return value if value else None
        finally:
            curses.noecho()
            curses.curs_set(0)

    @staticmethod
    def _draw_footer(stdscr: "curses._CursesWindow", message: str) -> None:
        height, width = stdscr.getmaxyx()
        if height < 4 or width < 4:
            return
        sep_row = height - 3
        msg_row = height - 2
        footer = message[: max(1, width - 4)]
        try:
            stdscr.hline(sep_row, 1, curses.ACS_HLINE, max(1, width - 2))
            stdscr.addstr(msg_row, 2, footer)
        except curses.error:
            pass  # Terminal too small — skip drawing footer

