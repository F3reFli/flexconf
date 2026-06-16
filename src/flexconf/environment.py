from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


# External commands FlexConf relies on to snapshot/apply a theme.
_REQUIRED_COMMANDS: tuple[str, ...] = ("dconf", "gsettings")
# Commands that are nice to have but not strictly required.
_OPTIONAL_COMMANDS: tuple[str, ...] = ("gnome-extensions",)


@dataclass(frozen=True)
class Environment:
    """Snapshot of the host capabilities FlexConf cares about.

    Computed once at startup so the UI can warn the user instead of failing
    half-way through a snapshot/apply on an unsupported host.
    """

    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    desktop: str
    session_type: str
    is_gnome: bool

    @property
    def is_ready(self) -> bool:
        """True when every mandatory command is available on the PATH."""
        return not self.missing_required

    def summary(self) -> str:
        """One-line, human-friendly capability summary for the splash/footer."""
        desktop = self.desktop or "inconnu"
        if self.is_ready:
            return f"Environnement OK — {desktop} ({self.session_type or '?'})"
        joined = ", ".join(self.missing_required)
        return f"Commandes manquantes: {joined}"

    def warnings(self) -> tuple[str, ...]:
        """Non-fatal advisories worth surfacing to the user."""
        notes: list[str] = []
        if self.missing_optional:
            notes.append(
                "optionnel absent: " + ", ".join(self.missing_optional)
            )
        if not self.is_gnome and self.is_ready:
            notes.append("bureau non-GNOME détecté — support limité")
        return tuple(notes)


def detect_environment() -> Environment:
    """Inspect the host for the tooling and desktop FlexConf expects.

    Safe to call on any platform: it only reads environment variables and
    looks commands up on the PATH, never executing anything.
    """
    missing_required = tuple(
        name for name in _REQUIRED_COMMANDS if shutil.which(name) is None
    )
    missing_optional = tuple(
        name for name in _OPTIONAL_COMMANDS if shutil.which(name) is None
    )

    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("XDG_SESSION_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or ""
    )
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    is_gnome = "gnome" in desktop.lower() or "ubuntu" in desktop.lower()

    return Environment(
        missing_required=missing_required,
        missing_optional=missing_optional,
        desktop=desktop,
        session_type=session_type,
        is_gnome=is_gnome,
    )
