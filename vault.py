"""Central Vault class for path resolution and config reading."""

import json
from pathlib import Path
from typing import Iterator


class Vault:
    """Represents an Obsidian vault on disk."""

    EXCLUDED_DIRS = {".obsidian", ".trash", ".git", ".venv", "node_modules"}

    def __init__(self, vault_path: str | Path):
        self.root = Path(vault_path).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"Vault path does not exist: {self.root}")

    def resolve_path(self, name_or_path: str) -> Path | None:
        """Resolve a vault-relative path or note name to an absolute Path.

        Resolution order (mirrors Obsidian):
        1. Exact path match
        2. Filename match with .md appended
        3. Case-insensitive filename match
        """
        # Normalize: strip leading slashes, ensure .md extension for searching
        name_or_path = name_or_path.strip("/")

        # 1. Exact match
        candidate = self.root / name_or_path
        if candidate.is_file() and self._is_within_vault(candidate):
            return candidate

        # Try with .md appended
        if not name_or_path.endswith(".md"):
            candidate = self.root / (name_or_path + ".md")
            if candidate.is_file() and self._is_within_vault(candidate):
                return candidate

        # 2. Filename match anywhere in vault
        basename = Path(name_or_path).name
        if not basename.endswith(".md"):
            basename += ".md"

        matches = list(self.root.rglob(basename))
        matches = [m for m in matches if self._is_within_vault(m) and m.is_file()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Ambiguous — return first match (sorted for determinism)
            return sorted(matches)[0]

        # 3. Case-insensitive filename match
        basename_lower = basename.lower()
        for p in self.root.rglob("*.md"):
            if p.name.lower() == basename_lower and self._is_within_vault(p):
                return p

        return None

    def _is_within_vault(self, path: Path) -> bool:
        """Check that a path resolves to within the vault root."""
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.root))
        except (OSError, ValueError):
            return False

    def ensure_path(self, vault_relative: str) -> Path:
        """Convert a vault-relative path to absolute, creating parent dirs.

        Appends .md if not present. Does NOT check if file exists.
        """
        vault_relative = vault_relative.strip("/")
        if not vault_relative.endswith(".md"):
            vault_relative += ".md"
        full = self.root / vault_relative
        if not self._is_within_vault(full):
            raise ValueError(f"Path escapes vault: {vault_relative}")
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def read_config(self, filename: str) -> dict:
        """Read a JSON config file from .obsidian/. Returns {} if missing."""
        config_path = self.root / ".obsidian" / filename
        if not config_path.is_file():
            return {}
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    @property
    def daily_notes_config(self) -> dict:
        """Daily notes settings with defaults."""
        config = self.read_config("daily-notes.json")
        return {
            "folder": config.get("folder", ""),
            "format": config.get("format", "YYYY-MM-DD"),
            "template": config.get("template", ""),
        }

    @property
    def templates_config(self) -> dict:
        """Templates settings with defaults."""
        config = self.read_config("templates.json")
        return {
            "folder": config.get("folder", "Templates"),
        }

    def iter_notes(
        self, folder: str = "", recursive: bool = False, max_depth: int = 2
    ) -> Iterator[Path]:
        """Yield .md files in the vault, optionally within a folder."""
        base = self.root / folder if folder else self.root

        if not base.is_dir():
            return

        if recursive:
            for p in sorted(base.rglob("*.md")):
                if self._should_include(p) and self._within_depth(p, base, max_depth):
                    yield p
        else:
            for p in sorted(base.iterdir()):
                if p.is_file() and p.suffix == ".md" and self._should_include(p):
                    yield p

    def iter_entries(
        self, folder: str = "", recursive: bool = False, max_depth: int = 2
    ) -> Iterator[Path]:
        """Yield all files and directories (not just .md) in a folder."""
        base = self.root / folder if folder else self.root

        if not base.is_dir():
            return

        if recursive:
            for p in sorted(base.rglob("*")):
                if self._should_include(p) and self._within_depth(p, base, max_depth):
                    yield p
        else:
            for p in sorted(base.iterdir()):
                if self._should_include(p):
                    yield p

    def _should_include(self, path: Path) -> bool:
        """Check if a path should be included (not in excluded dirs)."""
        parts = path.relative_to(self.root).parts
        return not any(part in self.EXCLUDED_DIRS for part in parts)

    def _within_depth(self, path: Path, base: Path, max_depth: int) -> bool:
        """Check if a path is within the max depth from base."""
        rel = path.relative_to(base)
        return len(rel.parts) <= max_depth

    def note_count(self) -> int:
        """Count all .md files in the vault."""
        return sum(1 for _ in self.iter_notes(recursive=True, max_depth=100))

    def folder_count(self) -> int:
        """Count all folders in the vault (excluding hidden/excluded)."""
        count = 0
        for p in self.root.rglob("*"):
            if p.is_dir() and self._should_include(p):
                count += 1
        return count
