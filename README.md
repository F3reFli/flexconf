<div align="center">

# FlexConf

![Ubuntu](https://img.shields.io/badge/Ubuntu-000000?style=for-the-badge&logo=ubuntu&logoColor=white)
![GNOME](https://img.shields.io/badge/GNOME-000000?style=for-the-badge&logo=gnome&logoColor=white)
![Python](https://img.shields.io/badge/Python-000000?style=for-the-badge&logo=python&logoColor=white)
![Neovim](https://img.shields.io/badge/NeoVim-000000?style=for-the-badge&logo=neovim&logoColor=white)
![Kitty](https://img.shields.io/badge/Kitty-000000?style=for-the-badge&logo=gnometerminal&logoColor=white)

</div>

FlexConf is a terminal user interface (TUI) application for Ubuntu/GNOME that lets you snapshot your current desktop configuration and restore it at any time. It manages editor configs, terminal themes, wallpapers, GNOME settings, and more — all from a single command.

---

## Requirements

- Ubuntu 22.04 → 26.04 LTS (any GNOME-based distribution)
- Python 3.11+ (tested up to Python 3.14)
- `dconf` and `gsettings` (included by default on Ubuntu)

On startup FlexConf probes the host and tells you up front if `dconf`/`gsettings`
are missing or if a non-GNOME desktop is detected, instead of failing mid-operation.

---

## Installation

### From source

```bash
git clone https://github.com/F3reFli/flexconf.git
cd flexconf
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### System-wide (optional)

To make the `flexconf` command available without activating the virtual environment each time:

```bash
pip install --user -e .
```

Ensure `~/.local/bin` is in your `PATH`.

---

## Usage

```bash
flexconf
```

Or via the module:

```bash
python3 -m flexconf
```

On launch you get an animated splash screen that detects your environment and
loads the available themes, then a colored, boxed menu: **Choisir un thème**
(apply a theme, with a confirmation step), **Prendre un snapshot** (save the
current configuration), and **Quitter**.

### Key bindings

| Key | Action |
|-----|--------|
| `↑` / `↓` or `k` / `j` | Move the selection |
| `PgUp` / `PgDn`, `Home` / `End` | Jump through long lists |
| `Enter` | Validate the highlighted entry |
| `←` / `→` or `y` / `n` | Answer a confirmation dialog |
| `q` / `Esc` | Go back / quit |
| any key | Skip the splash animation |

---

## Theme structure

Themes are stored under `themes/<name>/`. Each theme directory may contain:

```
themes/
└── MyTheme/
    ├── manifest.json          # Theme metadata (auto-generated)
    ├── nvim/                  # Neovim config  (~/.config/nvim)
    ├── btop/                  # btop config    (~/.config/btop)
    ├── kitty/                 # kitty config   (~/.config/kitty)
    ├── wofi/                  # wofi config    (~/.config/wofi)
    ├── starship/              # Starship config (~/.config/starship.toml)
    ├── wallpaper/             # GNOME wallpaper
    └── ubuntu-settings/
        └── settings.dconf     # dconf export of /org/gnome/
```

### manifest.json

```json
{
  "theme_name": "MyTheme",
  "config_targets": {
    "nvim":     { "saved": true, "source": "/home/user/.config/nvim" },
    "btop":     { "saved": true, "source": "/home/user/.config/btop" },
    "kitty":    { "saved": true, "source": "/home/user/.config/kitty" },
    "wofi":     { "saved": true, "source": "/home/user/.config/wofi" },
    "starship": { "saved": true, "source": "/home/user/.config/starship.toml" }
  },
  "wallpaper_saved": true,
  "gnome_settings_saved": true
}
```

---

## Managed targets

| Target | Source |
|--------|--------|
| Neovim | `~/.config/nvim` |
| btop | `~/.config/btop` |
| kitty | `~/.config/kitty` |
| wofi | `~/.config/wofi` |
| Starship | `~/.config/starship.toml` |
| GNOME wallpaper | via `gsettings` |
| GNOME settings | via `dconf dump/load /org/gnome/` |
| GNOME extensions | via `dconf` |
| Firefox profile | auto-detected |

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `FLEXCONF_HOME` | Override the target user home directory |
| `FLEXCONF_THEMES_DIR` | Override the themes directory path |

Example:

```bash
FLEXCONF_THEMES_DIR=~/my-themes flexconf
```

---

## Development

### Running tests

```bash
python3 -m pytest tests/ -v
```

### Project layout

```
flexconf/
├── src/
│   └── flexconf/
│       ├── cli.py        # Entry point
│       ├── config.py     # Path resolution and configuration
│       ├── manager.py    # Save and restore logic
│       └── tui.py        # Terminal UI
├── tests/
│   └── test_manager.py
├── themes/               # Your themes (not tracked by git)
└── pyproject.toml
```

---

## License

This project is open-source.
