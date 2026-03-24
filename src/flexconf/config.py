from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

# Maps a target name to its path relative to ~/.config/
CONFIG_TARGETS: dict[str, str] = {
    "nvim": "nvim",
    "btop": "btop",
    "kitty": "kitty",
    "wofi": "wofi",
    "starship": "starship.toml",
}

# Candidate locations for the Firefox profile root (in priority order).
_FIREFOX_ROOTS: tuple[str, ...] = (
    "snap/firefox/common/.mozilla/firefox",
    ".mozilla/firefox",
)


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    home_dir: Path
    themes_dir: Path

    @classmethod
    def from_environment(cls, repo_root: Path) -> "AppPaths":
        home_dir = Path(os.environ.get("FLEXCONF_HOME", Path.home())).expanduser()
        themes_dir = Path(
            os.environ.get("FLEXCONF_THEMES_DIR", repo_root / "themes")
        ).expanduser()
        return cls(repo_root=repo_root, home_dir=home_dir, themes_dir=themes_dir)

    def config_sources(self) -> dict[str, Path]:
        config_root = self.home_dir / ".config"
        return {name: config_root / relative for name, relative in CONFIG_TARGETS.items()}

    def gnome_extensions_dir(self) -> Path:
        """Return the path to locally-installed GNOME Shell extensions."""
        return self.home_dir / ".local" / "share" / "gnome-shell" / "extensions"

    def firefox_profile_path(self) -> Path | None:
        """Return the default Firefox profile directory, or *None* if not found."""
        for relative in _FIREFOX_ROOTS:
            firefox_root = self.home_dir / relative
            profiles_ini = firefox_root / "profiles.ini"
            if not profiles_ini.exists():
                continue
            profile_dir = _parse_default_profile(profiles_ini, firefox_root)
            if profile_dir is not None and profile_dir.is_dir():
                return profile_dir
        return None


def _parse_default_profile(profiles_ini: Path, firefox_root: Path) -> Path | None:
    """Parse *profiles.ini* and return the path to the default profile."""
    parser = configparser.ConfigParser()
    parser.read(profiles_ini, encoding="utf-8")
    for section in parser.sections():
        if not section.startswith("Profile"):
            continue
        if parser.get(section, "Default", fallback="0") == "1":
            relative = parser.getboolean(section, "IsRelative", fallback=True)
            raw_path = parser.get(section, "Path", fallback=None)
            if raw_path is None:
                continue
            if relative:
                return firefox_root / raw_path
            return Path(raw_path)
    return None
