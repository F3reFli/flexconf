from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flexconf.config import AppPaths
from flexconf.manager import ThemeManager


class FakeRunner:
    def __init__(
        self,
        wallpaper_uri: str,
        dconf_dump: str,
        enabled_extensions: str = "['ext-a@test', 'ext-b@test']",
        extensions_dconf: str = "[ext-a]\nkey=value\n",
    ) -> None:
        self.wallpaper_uri = wallpaper_uri
        self.dconf_dump = dconf_dump
        self.enabled_extensions = enabled_extensions
        self.extensions_dconf = extensions_dconf
        self.calls: list[tuple[list[str], str | None]] = []

    def run(self, args: list[str], *, input_text: str | None = None) -> str:
        self.calls.append((args, input_text))

        if args[:4] == [
            "gsettings",
            "get",
            "org.gnome.desktop.background",
            "picture-uri",
        ]:
            return self.wallpaper_uri
        if args[:3] == ["dconf", "dump", "/org/gnome/"]:
            return self.dconf_dump
        if args[:3] == ["dconf", "load", "/org/gnome/"]:
            return ""
        if args[:3] == ["dconf", "reset", "-f"]:
            return ""
        if args[:4] == [
            "gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri",
        ]:
            return ""
        if args[:4] == [
            "gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri-dark",
        ]:
            return ""
        if args[:4] == [
            "gsettings",
            "get",
            "org.gnome.shell",
            "enabled-extensions",
        ]:
            return self.enabled_extensions
        if args[:4] == [
            "gsettings",
            "set",
            "org.gnome.shell",
            "enabled-extensions",
        ]:
            return ""
        if args[:3] == ["dconf", "dump", "/org/gnome/shell/extensions/"]:
            return self.extensions_dconf
        if args[:3] == ["dconf", "load", "/org/gnome/shell/extensions/"]:
            return ""
        raise AssertionError(f"Commande inattendue: {args}")


class ThemeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo_root = Path(self.temp_dir.name)
        self.home_dir = self.repo_root / "home"
        self.themes_dir = self.repo_root / "themes"
        self.wallpaper_file = self.repo_root / "wallpaper.png"
        self.wallpaper_file.write_text("png-data", encoding="utf-8")

        self._write_config("nvim", "init.lua", "vim.o.background = 'dark'")
        self._write_config("btop", "btop.conf", "color_theme = gruvbox")
        self._write_config("kitty", "kitty.conf", "background #000000")
        self._write_config("wofi", "style.css", "* { color: white; }")
        self._write_config_file("starship.toml", "format = '$all'")

        # Set up fake GNOME extensions
        self._setup_gnome_extensions()

        # Set up a fake Firefox profile
        self._setup_firefox_profile()

        self.paths = AppPaths(
            repo_root=self.repo_root,
            home_dir=self.home_dir,
            themes_dir=self.themes_dir,
        )
        self.runner = FakeRunner(
            wallpaper_uri=f"'{self.wallpaper_file.as_uri()}'",
            dconf_dump="[desktop/background]\npicture-uri='file:///tmp/example.png'\n",
        )
        self.manager = ThemeManager(self.paths, runner=self.runner)

    def _setup_gnome_extensions(self) -> None:
        ext_dir = self.home_dir / ".local" / "share" / "gnome-shell" / "extensions"
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Create two fake extensions
        ext_a = ext_dir / "ext-a@test"
        ext_a.mkdir()
        (ext_a / "metadata.json").write_text(
            json.dumps({"uuid": "ext-a@test", "name": "Extension A"}),
            encoding="utf-8",
        )
        (ext_a / "extension.js").write_text("// ext A code", encoding="utf-8")

        ext_b = ext_dir / "ext-b@test"
        ext_b.mkdir()
        (ext_b / "metadata.json").write_text(
            json.dumps({"uuid": "ext-b@test", "name": "Extension B"}),
            encoding="utf-8",
        )
        (ext_b / "extension.js").write_text("// ext B code", encoding="utf-8")

    def _setup_firefox_profile(self) -> None:
        ff_root = self.home_dir / ".mozilla" / "firefox"
        ff_root.mkdir(parents=True, exist_ok=True)

        # Write profiles.ini
        (ff_root / "profiles.ini").write_text(
            "[Profile0]\nName=default\nIsRelative=1\nPath=abc123.default\nDefault=1\n\n"
            "[General]\nStartWithLastProfile=1\nVersion=2\n",
            encoding="utf-8",
        )

        self.ff_profile = ff_root / "abc123.default"
        self.ff_profile.mkdir()

        # Write extensions.json with an active theme
        extensions = {
            "addons": [
                {
                    "id": "{test-theme-id}",
                    "type": "theme",
                    "active": True,
                    "defaultLocale": {"name": "Test Dark Theme"},
                },
                {
                    "id": "default-theme@mozilla.org",
                    "type": "theme",
                    "active": False,
                    "defaultLocale": {"name": "System theme"},
                },
            ]
        }
        (self.ff_profile / "extensions.json").write_text(
            json.dumps(extensions), encoding="utf-8"
        )

        # Write a prefs.js with toolbar theme
        (self.ff_profile / "prefs.js").write_text(
            'user_pref("browser.theme.toolbar-theme", 0);\n'
            'user_pref("extensions.activeThemeID", "{test-theme-id}");\n',
            encoding="utf-8",
        )

        # Write a chrome/ directory
        chrome_dir = self.ff_profile / "chrome"
        chrome_dir.mkdir()
        (chrome_dir / "userChrome.css").write_text(
            "#TabsToolbar { visibility: collapse; }", encoding="utf-8"
        )
        (chrome_dir / "userContent.css").write_text(
            "@-moz-document url(about:blank) { body { background: #111; } }",
            encoding="utf-8",
        )

    def _write_config(self, service: str, filename: str, content: str) -> None:
        target = self.home_dir / ".config" / service
        target.mkdir(parents=True, exist_ok=True)
        (target / filename).write_text(content, encoding="utf-8")

    def _write_config_file(self, filename: str, content: str) -> None:
        target = self.home_dir / ".config" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def test_snapshot_creates_theme_structure(self) -> None:
        result = self.manager.snapshot_theme("Nord")

        self.assertEqual(result.theme_name, "Nord")
        self.assertTrue((self.themes_dir / "Nord" / "nvim" / "init.lua").exists())
        self.assertTrue((self.themes_dir / "Nord" / "btop" / "btop.conf").exists())
        self.assertTrue((self.themes_dir / "Nord" / "kitty" / "kitty.conf").exists())
        self.assertTrue((self.themes_dir / "Nord" / "wofi" / "style.css").exists())
        self.assertTrue((self.themes_dir / "Nord" / "starship").exists())
        self.assertFalse((self.themes_dir / "Nord" / "starship").is_dir())
        self.assertTrue(
            (self.themes_dir / "Nord" / "wallpaper" / self.wallpaper_file.name).exists()
        )
        self.assertEqual(
            (self.themes_dir / "Nord" / "ubuntu-settings" / "settings.dconf").read_text(
                encoding="utf-8"
            ),
            self.runner.dconf_dump,
        )

        metadata = json.loads(
            (self.themes_dir / "Nord" / "wallpaper" / "metadata.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(metadata["asset_name"], self.wallpaper_file.name)

        # Firefox theme saved
        firefox_theme = json.loads(
            (self.themes_dir / "Nord" / "firefox" / "theme.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(firefox_theme["active_theme_id"], "{test-theme-id}")
        self.assertEqual(firefox_theme["theme_name"], "Test Dark Theme")
        self.assertTrue(
            (self.themes_dir / "Nord" / "firefox" / "chrome" / "userChrome.css").exists()
        )

        # GNOME extensions saved
        ext_meta = json.loads(
            (self.themes_dir / "Nord" / "gnome-extensions" / "metadata.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(sorted(ext_meta["installed"]), ["ext-a@test", "ext-b@test"])
        self.assertIn("ext-a@test", ext_meta["enabled_raw"])
        self.assertTrue(
            (
                self.themes_dir / "Nord" / "gnome-extensions" / "ext-a@test" / "extension.js"
            ).exists()
        )
        self.assertTrue(
            (self.themes_dir / "Nord" / "gnome-extensions" / "extensions.dconf").exists()
        )

        self.assertFalse(result.warnings)

    def test_apply_theme_restores_files_and_runs_commands(self) -> None:
        self.manager.snapshot_theme("Gruvbox")

        (self.home_dir / ".config" / "nvim" / "init.lua").write_text(
            "vim.o.background = 'light'",
            encoding="utf-8",
        )
        (self.home_dir / ".config" / "kitty" / "kitty.conf").write_text(
            "background #ffffff",
            encoding="utf-8",
        )

        result = self.manager.apply_theme("Gruvbox")

        self.assertEqual(
            (self.home_dir / ".config" / "nvim" / "init.lua").read_text(encoding="utf-8"),
            "vim.o.background = 'dark'",
        )
        self.assertEqual(
            (self.home_dir / ".config" / "kitty" / "kitty.conf").read_text(
                encoding="utf-8"
            ),
            "background #000000",
        )
        self.assertFalse(result.warnings)

        commands = [call[0] for call in self.runner.calls]
        self.assertIn(["dconf", "load", "/org/gnome/"], commands)
        self.assertIn(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                (self.themes_dir / "Gruvbox" / "wallpaper" / self.wallpaper_file.name).as_uri(),
            ],
            commands,
        )


    def test_snapshot_and_apply_restores_firefox(self) -> None:
        self.manager.snapshot_theme("DarkTheme")

        # Modify Firefox chrome after snapshot
        (self.ff_profile / "chrome" / "userChrome.css").write_text(
            "/* changed */", encoding="utf-8"
        )
        # Remove user.js if it exists
        user_js = self.ff_profile / "user.js"
        if user_js.exists():
            user_js.unlink()

        result = self.manager.apply_theme("DarkTheme")

        # chrome/ restored
        self.assertEqual(
            (self.ff_profile / "chrome" / "userChrome.css").read_text(encoding="utf-8"),
            "#TabsToolbar { visibility: collapse; }",
        )
        # user.js written with theme ID
        self.assertTrue(user_js.exists())
        user_js_content = user_js.read_text(encoding="utf-8")
        self.assertIn("{test-theme-id}", user_js_content)
        self.assertFalse(result.warnings)


    def test_snapshot_and_apply_restores_gnome_extensions(self) -> None:
        self.manager.snapshot_theme("ExtTheme")

        ext_dir = self.home_dir / ".local" / "share" / "gnome-shell" / "extensions"

        # Modify extension file after snapshot
        (ext_dir / "ext-a@test" / "extension.js").write_text(
            "// modified", encoding="utf-8"
        )

        result = self.manager.apply_theme("ExtTheme")

        # Extension files are intentionally NOT restored on disk — replacing live
        # extension directories while GNOME Shell is running crashes the compositor.
        self.assertEqual(
            (ext_dir / "ext-a@test" / "extension.js").read_text(encoding="utf-8"),
            "// modified",
        )

        # enabled-extensions must be set via gsettings
        commands = [call[0] for call in self.runner.calls]
        set_cmds = [c for c in commands if c[:4] == [
            "gsettings", "set", "org.gnome.shell", "enabled-extensions"
        ]]
        self.assertTrue(len(set_cmds) > 0)

        # Extension settings must be loaded separately via
        # dconf load /org/gnome/shell/extensions/
        ext_loads = [c for c in commands if c[:3] == [
            "dconf", "load", "/org/gnome/shell/extensions/"
        ]]
        self.assertTrue(len(ext_loads) > 0)

        # No dconf reset must ever happen (crashes GNOME Shell)
        resets = [c for c in commands if c[:2] == ["dconf", "reset"]]
        self.assertEqual(len(resets), 0)

        self.assertFalse(result.warnings)


if __name__ == "__main__":
    unittest.main()
