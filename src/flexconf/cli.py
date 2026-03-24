from __future__ import annotations

from pathlib import Path

from flexconf.config import AppPaths
from flexconf.manager import ThemeError, ThemeManager
from flexconf.tui import FlexConfTUI


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    paths = AppPaths.from_environment(repo_root)
    manager = ThemeManager(paths)
    app = FlexConfTUI(manager)

    try:
        app.run()
    except KeyboardInterrupt:
        return 130
    except ThemeError as error:
        print(f"Erreur: {error}")
        return 1
    return 0
