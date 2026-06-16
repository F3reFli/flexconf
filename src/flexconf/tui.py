from __future__ import annotations

import curses

from flexconf import ui
from flexconf.environment import Environment, detect_environment
from flexconf.manager import ThemeError, ThemeManager
from flexconf.splash import LoadStep, run_splash
from flexconf.ui import Status


class FlexConfTUI:
    def __init__(self, manager: ThemeManager) -> None:
        self.manager = manager
        self.status = Status.info("Prêt.")
        self.environment: Environment | None = None

    def run(self) -> None:
        curses.wrapper(self._main)

    def _main(self, stdscr: "curses._CursesWindow") -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # Some terminals don't support cursor visibility control
        stdscr.keypad(True)
        ui.init_colors()

        self._boot(stdscr)

        while True:
            choice = self._menu(
                stdscr,
                "FlexConf",
                ["Choisir un thème", "Prendre un snapshot", "Quitter"],
                subtitle=self._subtitle(),
            )
            if choice == 0:
                self._choose_theme(stdscr)
            elif choice == 1:
                self._take_snapshot(stdscr)
            else:
                return

    def _boot(self, stdscr: "curses._CursesWindow") -> None:
        """Run the animated splash while detecting the host and loading themes."""
        env_box: dict[str, Environment] = {}
        themes_box: dict[str, list[str]] = {}

        steps = [
            LoadStep(
                "Détection de l'environnement…",
                lambda: env_box.__setitem__("env", detect_environment()),
            ),
            LoadStep(
                "Chargement des thèmes…",
                lambda: themes_box.__setitem__("themes", self.manager.list_themes()),
            ),
        ]
        try:
            run_splash(stdscr, steps)
        except curses.error:
            # Tiny terminal — skip the animation, still finish the work.
            for step in steps:
                step.action()

        self.environment = env_box.get("env")
        self.status = self._initial_status(themes_box.get("themes", []))

    def _initial_status(self, themes: list[str]) -> Status:
        env = self.environment
        if env is not None and not env.is_ready:
            return Status.error(env.summary())
        count = len(themes)
        label = "thème" if count == 1 else "thèmes"
        message = f"{count} {label} disponible{'s' if count > 1 else ''}."
        warnings = env.warnings() if env else ()
        if warnings:
            return Status.warning(f"{message}  ⚠ {warnings[0]}")
        return Status.success(message)

    def _subtitle(self) -> str:
        if self.environment is None:
            return ""
        return self.environment.summary()

    def _choose_theme(self, stdscr: "curses._CursesWindow") -> None:
        themes = self.manager.list_themes()
        if not themes:
            self.status = Status.warning("Aucun thème disponible dans themes/.")
            return

        options = themes + ["← Retour"]
        selected = self._menu(
            stdscr, "Choisir un thème", options, subtitle="Entrée pour appliquer"
        )
        if selected == len(options) - 1:
            return

        theme_name = options[selected]
        if not self._confirm(stdscr, f"Appliquer « {theme_name} » ?"):
            self.status = Status.info("Application annulée.")
            return

        try:
            result = self.manager.apply_theme(theme_name)
        except ThemeError as error:
            self.status = Status.error(str(error))
            return
        self.status = self._result_status(result.format_message("Application"), result.warnings)

    def _take_snapshot(self, stdscr: "curses._CursesWindow") -> None:
        snapshot_name = self._prompt(stdscr, "Nom du snapshot")
        if snapshot_name is None:
            self.status = Status.info("Snapshot annulé.")
            return

        try:
            result = self.manager.snapshot_theme(snapshot_name)
        except ThemeError as error:
            self.status = Status.error(str(error))
            return
        self.status = self._result_status(result.format_message("Snapshot"), result.warnings)

    @staticmethod
    def _result_status(message: str, warnings: tuple[str, ...]) -> Status:
        return Status.warning(message) if warnings else Status.success(message)

    # ------------------------------------------------------------------ menu

    def _menu(
        self,
        stdscr: "curses._CursesWindow",
        title: str,
        options: list[str],
        *,
        subtitle: str = "",
    ) -> int:
        index = 0
        scroll = 0

        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()

            box_w = min(max(40, len(title) + 10), max(20, width - 4))
            visible = max(1, min(len(options), height - 10))
            box_h = visible + 4
            box_top = max(1, (height - box_h - 4) // 2)
            box_left = max(0, (width - box_w) // 2)

            self._draw_header(stdscr, width, title, subtitle, box_top)

            ui.draw_box(
                stdscr, box_top + 2, box_left, box_h, box_w,
                title="menu", attr=ui.color(ui.PAIR_DIM),
            )

            if index < scroll:
                scroll = index
            elif index >= scroll + visible:
                scroll = index - visible + 1

            for slot in range(visible):
                opt_idx = scroll + slot
                if opt_idx >= len(options):
                    break
                y = box_top + 3 + slot
                selected = opt_idx == index
                prefix = " ▸ " if selected else "   "
                label = options[opt_idx][: box_w - 6]
                text = (prefix + label).ljust(box_w - 2)
                attr = (
                    ui.color(ui.PAIR_SELECT) | curses.A_BOLD
                    if selected
                    else ui.color(ui.PAIR_DIM)
                )
                ui.safe_addstr(stdscr, y, box_left + 1, text, attr)

            if scroll > 0:
                ui.safe_addstr(stdscr, box_top + 3, box_left + box_w - 3, "▲", ui.color(ui.PAIR_ACCENT))
            if scroll + visible < len(options):
                ui.safe_addstr(stdscr, box_top + box_h, box_left + box_w - 3, "▼", ui.color(ui.PAIR_ACCENT))

            self._draw_footer(stdscr, "↑/↓ ou j/k · Entrée valider · q quitter")
            stdscr.refresh()

            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                index = (index - 1) % len(options)
            elif key in (curses.KEY_DOWN, ord("j")):
                index = (index + 1) % len(options)
            elif key in (curses.KEY_PPAGE,):
                index = max(0, index - visible)
            elif key in (curses.KEY_NPAGE,):
                index = min(len(options) - 1, index + visible)
            elif key in (curses.KEY_HOME,):
                index = 0
            elif key in (curses.KEY_END,):
                index = len(options) - 1
            elif key in (10, 13, curses.KEY_ENTER):
                return index
            elif key in (27, ord("q")):
                return len(options) - 1

    def _confirm(self, stdscr: "curses._CursesWindow", question: str) -> bool:
        """Small yes/no dialog. Returns True for yes. Defaults to no."""
        yes = False
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            box_w = min(max(len(question) + 8, 36), max(20, width - 4))
            box_h = 6
            box_top = max(1, (height - box_h) // 2)
            box_left = max(0, (width - box_w) // 2)

            ui.draw_box(stdscr, box_top, box_left, box_h, box_w, title="confirmer", attr=ui.color(ui.PAIR_WARNING))
            ui.safe_addstr(stdscr, box_top + 2, box_left + ui.center_x(box_w, question), question, ui.color(ui.PAIR_DIM) | curses.A_BOLD)

            yes_label = " Oui " if yes else "  Oui  "
            no_label = "  Non  " if yes else " Non "
            buttons = f"{yes_label}   {no_label}"
            attr_yes = ui.color(ui.PAIR_SELECT) | curses.A_BOLD if yes else ui.color(ui.PAIR_DIM)
            attr_no = ui.color(ui.PAIR_DIM) if yes else ui.color(ui.PAIR_SELECT) | curses.A_BOLD
            bx = box_left + ui.center_x(box_w, buttons)
            ui.safe_addstr(stdscr, box_top + 3, bx, yes_label, attr_yes)
            ui.safe_addstr(stdscr, box_top + 3, bx + len(yes_label) + 3, no_label, attr_no)

            self._draw_footer(stdscr, "←/→ ou y/n · Entrée valider")
            stdscr.refresh()

            key = stdscr.getch()
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT, ord("h"), ord("l"), ord("\t")):
                yes = not yes
            elif key in (ord("y"), ord("o")):
                return True
            elif key in (ord("n"),):
                return False
            elif key in (10, 13, curses.KEY_ENTER):
                return yes
            elif key in (27,):
                return False

    def _prompt(self, stdscr: "curses._CursesWindow", prompt: str) -> str | None:
        curses.curs_set(1)
        curses.echo()
        try:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            box_w = min(64, max(30, width - 4))
            box_h = 6
            box_top = max(1, (height - box_h) // 2)
            box_left = max(0, (width - box_w) // 2)

            ui.draw_box(stdscr, box_top, box_left, box_h, box_w, title=prompt, attr=ui.color(ui.PAIR_ACCENT))
            ui.safe_addstr(stdscr, box_top + 1, box_left + 2, "(vide + Entrée pour annuler)", ui.color(ui.PAIR_DIM) | curses.A_DIM)
            ui.safe_addstr(stdscr, box_top + 3, box_left + 2, "› ", ui.color(ui.PAIR_ACCENT) | curses.A_BOLD)

            self._draw_footer(stdscr, "Entrée pour valider")
            stdscr.refresh()
            raw = stdscr.getstr(box_top + 3, box_left + 4, box_w - 6)
            value = raw.decode("utf-8", errors="replace").strip()
            return value if value else None
        finally:
            curses.noecho()
            curses.curs_set(0)

    # --------------------------------------------------------------- chrome

    @staticmethod
    def _draw_header(stdscr, width: int, title: str, subtitle: str, box_top: int) -> None:
        brand = f"⟡ {title.upper()} ⟡"
        brand_row = max(0, box_top - 2)
        ui.safe_addstr(stdscr, brand_row, ui.center_x(width, brand), brand, ui.color(ui.PAIR_ACCENT) | curses.A_BOLD)
        if subtitle:
            ui.safe_addstr(stdscr, brand_row + 1, ui.center_x(width, subtitle), subtitle, ui.color(ui.PAIR_DIM) | curses.A_DIM)

    def _draw_footer(self, stdscr, hint: str) -> None:
        height, width = stdscr.getmaxyx()
        if height < 4 or width < 4:
            return
        sep_row = height - 3
        status_row = height - 2
        hint_row = height - 1

        try:
            stdscr.hline(sep_row, 1, curses.ACS_HLINE, max(1, width - 2))
        except curses.error:
            pass

        status = self.status
        ui.safe_addstr(stdscr, status_row, 2, status.text[: max(1, width - 4)], ui.color(status.pair) | curses.A_BOLD)
        ui.safe_addstr(stdscr, hint_row, 2, hint[: max(1, width - 4)], ui.color(ui.PAIR_DIM) | curses.A_DIM)
