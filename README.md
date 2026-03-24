# FlexConf

**FlexConf** est une application TUI (interface en mode texte) pour Ubuntu/GNOME qui permet de :

- 📸 **Sauvegarder** un snapshot complet de ta configuration actuelle (neovim, btop, kitty, wofi, starship, wallpaper, paramètres GNOME, extensions…)
- 🎨 **Appliquer** un thème sauvegardé en un seul raccourci
- 🗂️ **Gérer** plusieurs profils de configuration et basculer entre eux rapidement

---

## Prérequis

- Ubuntu 22.04+ (ou toute distribution GNOME)
- Python 3.11+
- `dconf` et `gsettings` disponibles (inclus par défaut sur Ubuntu)

---

## Installation

### Depuis le dépôt (recommandé)

```bash
git clone https://github.com/F3reFli/flexconf.git
cd flexconf
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### En tant que commande système (optionnel)

Pour avoir `flexconf` disponible sans activer le venv à chaque fois :

```bash
pip install --user -e .
```

> Assure-toi que `~/.local/bin` est dans ton `PATH`.

---

## Lancer l'application

```bash
# Avec le venv activé
flexconf

# Ou directement via le module
python3 -m flexconf
```

---

## Interface TUI

La TUI s'ouvre dans le terminal avec les actions suivantes :

| Touche | Action |
|--------|--------|
| `↑` / `↓` | Naviguer entre les thèmes |
| `Entrée` | Appliquer le thème sélectionné |
| `s` | Sauvegarder la configuration actuelle comme nouveau thème |
| `d` | Supprimer le thème sélectionné |
| `q` | Quitter |

---

## Structure d'un thème

Les thèmes sont stockés dans le dossier `themes/<nom>/`. Chaque thème peut contenir :

```
themes/
└── MonTheme/
    ├── manifest.json          # Métadonnées du thème (généré automatiquement)
    ├── nvim/                  # Config Neovim (~/.config/nvim)
    ├── btop/                  # Config btop (~/.config/btop)
    ├── kitty/                 # Config kitty (~/.config/kitty)
    ├── wofi/                  # Config wofi (~/.config/wofi)
    ├── starship/              # Config starship (~/.config/starship.toml)
    ├── wallpaper/             # Fond d'écran GNOME
    └── ubuntu-settings/
        └── settings.dconf     # Export dconf /org/gnome/
```

### Exemple de `manifest.json`

```json
{
  "theme_name": "MonTheme",
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

## Cibles gérées

FlexConf sauvegarde et restaure automatiquement :

| Cible | Source |
|-------|--------|
| Neovim | `~/.config/nvim` |
| btop | `~/.config/btop` |
| kitty | `~/.config/kitty` |
| wofi | `~/.config/wofi` |
| Starship | `~/.config/starship.toml` |
| Wallpaper GNOME | via `gsettings` |
| Paramètres GNOME | via `dconf dump/load /org/gnome/` |
| Extensions GNOME | via `dconf` |
| Profil Firefox | détecté automatiquement |

---

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `FLEXCONF_HOME` | Remplace le home utilisateur cible (utile pour les tests) |
| `FLEXCONF_THEMES_DIR` | Remplace le dossier `themes/` par un chemin personnalisé |

Exemple :

```bash
FLEXCONF_THEMES_DIR=~/mes-themes flexconf
```

---

## Développement

### Lancer les tests

```bash
python3 -m pytest tests/ -v
# ou
python3 -m unittest discover -s tests -v
```

### Structure du projet

```
flexconf/
├── src/
│   └── flexconf/
│       ├── cli.py       # Point d'entrée
│       ├── config.py    # Chemins et configuration
│       ├── manager.py   # Logique sauvegarde/restauration
│       └── tui.py       # Interface TUI
├── tests/
│   └── test_manager.py
├── themes/              # Tes thèmes (non versionnés)
└── pyproject.toml
```

---

## Licence

Ce projet est open-source. Fais-en bon usage ! 🚀
