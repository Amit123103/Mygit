import fnmatch
from pathlib import Path
from typing import List


class IgnoreMatcher:
    """Parses and evaluates .mygitignore patterns."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.patterns: List[str] = [
            ".mygit",
            ".mygit/*",
            ".git",
            "__pycache__",
            "*.pyc",
            ".venv",
            "venv",
            "node_modules",
        ]
        self._load_ignore_files()

    def _load_ignore_files(self):
        ignore_file = self.root_dir / ".mygitignore"
        if ignore_file.is_file():
            try:
                content = ignore_file.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.patterns.append(line)
            except Exception:
                pass

    def is_ignored(self, rel_path: str) -> bool:
        """Check if relative path string (e.g., 'src/api.py' or 'node_modules/foo.js') is ignored."""
        # Standardize path separators to forward slashes for matching
        normalized = rel_path.replace("\\", "/")
        parts = normalized.split("/")

        for pattern in self.patterns:
            pattern_norm = pattern.replace("\\", "/").rstrip("/")

            # Check if any parent folder matches exact directory pattern
            for part in parts:
                if fnmatch.fnmatch(part, pattern_norm):
                    return True

            if fnmatch.fnmatch(normalized, pattern_norm) or fnmatch.fnmatch(
                normalized, f"{pattern_norm}/*"
            ):
                return True

        return False
