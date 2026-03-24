from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from flexconf.config import AppPaths


class ThemeError(RuntimeError):
    """Raised when a theme operation fails."""


class CommandRunner:
    def run(self, args: list[str], *, input_text: str | None = None) -> str:
        raise NotImplementedError


class SubprocessRunner(CommandRunner):
    def run(self, args: list[str], *, input_text: str | None = None) -> str:
        try:
            completed = subprocess.run(
                args,
                input=input_text,
                text=True,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.strip() or error.stdout.strip() or "unknown command error"
            raise ThemeError(f"Commande echouee ({' '.join(args)}): {stderr}") from error
        return completed.stdout


@dataclass(frozen=True)
class OperationResult:
    theme_name: str
    warnings: tuple[str, ...] = ()

    def format_message(self, action: str) -> str:
        if not self.warnings:
            return f"{action} termine pour '{self.theme_name}'."
        return (
            f"{action} termine pour '{self.theme_name}' "
            f"avec avertissements: {', '.join(self.warnings)}."
        )


class ThemeManager:
    def __init__(self, paths: AppPaths, runner: CommandRunner | None = None) -> None:
        self.paths = paths
        self.runner = runner or SubprocessRunner()
        self.paths.themes_dir.mkdir(parents=True, exist_ok=True)

    def list_themes(self) -> list[str]:
        return sorted(
            path.name for path in self.paths.themes_dir.iterdir() if path.is_dir()
        )

    def snapshot_theme(self, raw_name: str) -> OperationResult:
        theme_name = self._normalize_theme_name(raw_name)
        theme_dir = self.paths.themes_dir / theme_name
        if theme_dir.exists():
            raise ThemeError(f"Le theme '{theme_name}' existe deja.")

        theme_dir.mkdir(parents=True)
        warnings: list[str] = []

        for target_name, source_path in self.paths.config_sources().items():
            destination = theme_dir / target_name
            if not source_path.exists():
                warnings.append(f"{target_name} absent")
                continue
            self._copy_path(source_path, destination)

        try:
            wallpaper_warning = self._snapshot_wallpaper(theme_dir)
        except ThemeError as error:
            wallpaper_warning = f"wallpaper: {error}"
        if wallpaper_warning is not None:
            warnings.append(wallpaper_warning)

        try:
            settings_warning = self._snapshot_gnome_settings(theme_dir)
        except ThemeError as error:
            settings_warning = f"ubuntu-settings: {error}"
        if settings_warning is not None:
            warnings.append(settings_warning)

        try:
            firefox_warning = self._snapshot_firefox(theme_dir)
        except ThemeError as error:
            firefox_warning = f"firefox: {error}"
        if firefox_warning is not None:
            warnings.append(firefox_warning)

        try:
            ext_warning = self._snapshot_gnome_extensions(theme_dir)
        except ThemeError as error:
            ext_warning = f"gnome-extensions: {error}"
        if ext_warning is not None:
            warnings.append(ext_warning)

        manifest = {
            "theme_name": theme_name,
            "config_targets": {
                name: {
                    "saved": (theme_dir / name).exists(),
                    "source": str(path),
                }
                for name, path in self.paths.config_sources().items()
            },
            "wallpaper_saved": (theme_dir / "wallpaper" / "metadata.json").exists(),
            "gnome_settings_saved": (
                theme_dir / "ubuntu-settings" / "settings.dconf"
            ).exists(),
            "firefox_saved": (theme_dir / "firefox" / "theme.json").exists(),
            "gnome_extensions_saved": (
                theme_dir / "gnome-extensions" / "metadata.json"
            ).exists(),
        }
        (theme_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return OperationResult(theme_name=theme_name, warnings=tuple(warnings))

    def apply_theme(self, theme_name: str) -> OperationResult:
        normalized_name = self._normalize_theme_name(theme_name)
        theme_dir = self.paths.themes_dir / normalized_name
        if not theme_dir.exists():
            raise ThemeError(f"Le theme '{normalized_name}' est introuvable.")

        warnings: list[str] = []

        for target_name, destination_path in self.paths.config_sources().items():
            themed_path = theme_dir / target_name
            if not themed_path.exists():
                warnings.append(f"{target_name} non defini")
                continue
            self._replace_path(themed_path, destination_path)

        try:
            settings_warning = self._apply_gnome_settings(theme_dir)
        except ThemeError as error:
            settings_warning = f"ubuntu-settings: {error}"
        if settings_warning is not None:
            warnings.append(settings_warning)

        try:
            wallpaper_warning = self._apply_wallpaper(theme_dir)
        except ThemeError as error:
            wallpaper_warning = f"wallpaper: {error}"
        if wallpaper_warning is not None:
            warnings.append(wallpaper_warning)

        try:
            firefox_warning = self._apply_firefox(theme_dir)
        except ThemeError as error:
            firefox_warning = f"firefox: {error}"
        if firefox_warning is not None:
            warnings.append(firefox_warning)

        try:
            ext_warning = self._apply_gnome_extensions(theme_dir)
        except ThemeError as error:
            ext_warning = f"gnome-extensions: {error}"
        if ext_warning is not None:
            warnings.append(ext_warning)

        return OperationResult(theme_name=normalized_name, warnings=tuple(warnings))

    def _snapshot_wallpaper(self, theme_dir: Path) -> str | None:
        wallpaper_dir = theme_dir / "wallpaper"
        wallpaper_dir.mkdir(parents=True, exist_ok=True)

        raw_uri = self.runner.run(
            ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"]
        ).strip()
        uri = self._strip_gsettings_quotes(raw_uri)
        metadata: dict[str, str | bool] = {
            "original_uri": uri,
            "copied_asset": False,
        }

        parsed = urlparse(uri)
        if parsed.scheme == "file":
            wallpaper_path = Path(parsed.path)
            if wallpaper_path.exists():
                asset_name = wallpaper_path.name
                shutil.copy2(wallpaper_path, wallpaper_dir / asset_name)
                metadata["copied_asset"] = True
                metadata["asset_name"] = asset_name
            else:
                metadata["missing_asset"] = True
                (wallpaper_dir / "metadata.json").write_text(
                    json.dumps(metadata, indent=2), encoding="utf-8"
                )
                return "wallpaper fichier absent"

        (wallpaper_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        return None

    def _snapshot_gnome_settings(self, theme_dir: Path) -> str | None:
        settings_dir = theme_dir / "ubuntu-settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings_dump = self.runner.run(["dconf", "dump", "/org/gnome/"])
        settings_file = settings_dir / "settings.dconf"
        settings_file.write_text(settings_dump, encoding="utf-8")
        if not settings_dump.strip():
            return "ubuntu-settings vides"
        return None

    def _apply_gnome_settings(self, theme_dir: Path) -> str | None:
        settings_file = theme_dir / "ubuntu-settings" / "settings.dconf"
        if not settings_file.exists():
            return "ubuntu-settings non defini"
        settings_text = settings_file.read_text(encoding="utf-8")

        # Load the full dump (general GNOME settings).
        self.runner.run(
            ["dconf", "load", "/org/gnome/"],
            input_text=settings_text,
        )

        # The full dump contains extension settings as [shell/extensions/X].
        # dconf load /org/gnome/ writes them, but some extensions don't react.
        # Re-load them via /org/gnome/shell/extensions/ with converted section
        # headers ([X] instead of [shell/extensions/X]) so extensions pick up
        # the changes reliably.  This also covers old themes that lack the
        # separate gnome-extensions/extensions.dconf file.
        ext_dump = self._extract_extension_sections(settings_text)
        if ext_dump:
            self.runner.run(
                ["dconf", "load", "/org/gnome/shell/extensions/"],
                input_text=ext_dump,
            )
        return None

    def _apply_wallpaper(self, theme_dir: Path) -> str | None:
        metadata_file = theme_dir / "wallpaper" / "metadata.json"
        if not metadata_file.exists():
            return "wallpaper non defini"

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        uri = str(metadata["original_uri"])
        if metadata.get("copied_asset"):
            asset_name = metadata.get("asset_name")
            if not asset_name:
                raise ThemeError("Le metadata du wallpaper est incomplet.")
            asset_path = (theme_dir / "wallpaper" / str(asset_name)).resolve()
            uri = asset_path.as_uri()

        self.runner.run(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                uri,
            ]
        )
        try:
            self.runner.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.background",
                    "picture-uri-dark",
                    uri,
                ]
            )
        except ThemeError:
            return "picture-uri-dark non applique"
        return None

    def _snapshot_gnome_extensions(self, theme_dir: Path) -> str | None:
        ext_src = self.paths.gnome_extensions_dir()
        if not ext_src.is_dir():
            return "gnome-extensions: dossier introuvable"

        ext_dir = theme_dir / "gnome-extensions"
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Copy every installed extension directory
        copied: list[str] = []
        for child in sorted(ext_src.iterdir()):
            if child.is_dir():
                shutil.copytree(child, ext_dir / child.name)
                copied.append(child.name)

        if not copied:
            return "gnome-extensions: aucune extension installee"

        # Save the enabled-extensions list via gsettings
        try:
            raw = self.runner.run(
                ["gsettings", "get", "org.gnome.shell", "enabled-extensions"]
            ).strip()
            enabled_list = self._strip_gsettings_quotes(raw)
        except ThemeError:
            enabled_list = "[]"

        # Save the per-extension dconf settings
        try:
            ext_settings = self.runner.run(
                ["dconf", "dump", "/org/gnome/shell/extensions/"]
            )
        except ThemeError:
            ext_settings = ""

        metadata = {
            "installed": copied,
            "enabled_raw": enabled_list,
            "source": str(ext_src),
        }
        (ext_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        if ext_settings.strip():
            (ext_dir / "extensions.dconf").write_text(ext_settings, encoding="utf-8")

        return None

    def _apply_gnome_extensions(self, theme_dir: Path) -> str | None:
        ext_dir = theme_dir / "gnome-extensions"
        if not ext_dir.exists():
            return "gnome-extensions non defini"

        metadata_file = ext_dir / "metadata.json"
        if not metadata_file.exists():
            return "gnome-extensions: metadata manquant"

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

        # Only restore the enabled-extensions list — never touch extension files
        # on disk while GNOME Shell is running (replacing loaded directories
        # crashes the compositor).
        enabled_raw = metadata.get("enabled_raw", "")
        if enabled_raw:
            try:
                self.runner.run(
                    [
                        "gsettings",
                        "set",
                        "org.gnome.shell",
                        "enabled-extensions",
                        enabled_raw,
                    ]
                )
            except ThemeError:
                pass

        # Load the dedicated extension settings dump if available (new themes).
        # For old themes this file doesn't exist and _apply_gnome_settings
        # already handles it via _extract_extension_sections.
        dconf_file = ext_dir / "extensions.dconf"
        if dconf_file.exists():
            settings_text = dconf_file.read_text(encoding="utf-8")
            if settings_text.strip():
                self.runner.run(
                    ["dconf", "load", "/org/gnome/shell/extensions/"],
                    input_text=settings_text,
                )

        return None

    def _snapshot_firefox(self, theme_dir: Path) -> str | None:
        profile_dir = self.paths.firefox_profile_path()
        if profile_dir is None:
            return "firefox: profil introuvable"

        firefox_dir = theme_dir / "firefox"
        firefox_dir.mkdir(parents=True, exist_ok=True)

        # Save chrome/ directory (userChrome.css / userContent.css)
        chrome_src = profile_dir / "chrome"
        if chrome_src.is_dir():
            shutil.copytree(chrome_src, firefox_dir / "chrome")

        # Extract active theme info from extensions.json
        extensions_file = profile_dir / "extensions.json"
        theme_info: dict[str, str | None] = {"active_theme_id": None, "theme_name": None}

        if extensions_file.exists():
            try:
                data = json.loads(extensions_file.read_text(encoding="utf-8"))
                for addon in data.get("addons", []):
                    if addon.get("type") == "theme" and addon.get("active"):
                        theme_info["active_theme_id"] = addon.get("id")
                        locale = addon.get("defaultLocale", {})
                        theme_info["theme_name"] = locale.get("name")
                        break
            except (json.JSONDecodeError, KeyError):
                pass

        # Extract toolbar theme pref
        prefs_file = profile_dir / "prefs.js"
        if prefs_file.exists():
            for line in prefs_file.read_text(encoding="utf-8").splitlines():
                if "browser.theme.toolbar-theme" in line:
                    theme_info["toolbar_theme_line"] = line.strip()
                    break

        (firefox_dir / "theme.json").write_text(
            json.dumps(theme_info, indent=2), encoding="utf-8"
        )
        return None

    def _apply_firefox(self, theme_dir: Path) -> str | None:
        firefox_dir = theme_dir / "firefox"
        if not firefox_dir.exists():
            return "firefox non defini"

        profile_dir = self.paths.firefox_profile_path()
        if profile_dir is None:
            return "firefox: profil introuvable"

        # Restore chrome/ directory
        chrome_src = firefox_dir / "chrome"
        chrome_dst = profile_dir / "chrome"
        if chrome_src.is_dir():
            self._replace_path(chrome_src, chrome_dst)

        # Apply theme via user.js (overrides prefs.js on next Firefox launch)
        theme_file = firefox_dir / "theme.json"
        if theme_file.exists():
            theme_info = json.loads(theme_file.read_text(encoding="utf-8"))
            active_id = theme_info.get("active_theme_id")
            if active_id:
                user_js = profile_dir / "user.js"
                existing = ""
                if user_js.exists():
                    existing = user_js.read_text(encoding="utf-8")

                # Remove any previous activeThemeID line we wrote
                lines = [
                    line
                    for line in existing.splitlines()
                    if "extensions.activeThemeID" not in line
                ]
                lines.append(
                    f'user_pref("extensions.activeThemeID", "{active_id}");'
                )
                user_js.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return None

    @staticmethod
    def _copy_path(source: Path, destination: Path) -> None:
        if source.is_dir():
            shutil.copytree(source, destination)
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    @staticmethod
    def _replace_path(source: Path, destination: Path) -> None:
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
            return
        shutil.copy2(source, destination)

    @staticmethod
    def _normalize_theme_name(raw_name: str) -> str:
        normalized = raw_name.strip()
        if not normalized:
            raise ThemeError("Le nom du theme ne peut pas etre vide.")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
        invalid = sorted({char for char in normalized if char not in allowed})
        if invalid:
            joined = "".join(invalid)
            raise ThemeError(f"Caracteres invalides dans le nom du theme: {joined}")
        return normalized

    @staticmethod
    def _extract_extension_sections(gnome_dump: str) -> str:
        """Convert ``[shell/extensions/X/…]`` sections from a full /org/gnome/
        dump into a standalone dump loadable at /org/gnome/shell/extensions/.

        ``[shell/extensions/openbar]``   -> ``[openbar]``
        ``[shell/extensions/blur/panel]`` -> ``[blur/panel]``
        Other sections are dropped.
        """
        prefix = "shell/extensions/"
        lines: list[str] = []
        inside = False
        for line in gnome_dump.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                path = stripped[1:-1]
                if path.startswith(prefix):
                    rest = path[len(prefix):]
                    lines.append(f"[{rest}]")
                    inside = True
                else:
                    inside = False
            elif inside:
                lines.append(line)
        return "\n".join(lines) + "\n" if lines else ""

    @staticmethod
    def _strip_gsettings_quotes(value: str) -> str:
        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            return value[1:-1]
        return value
