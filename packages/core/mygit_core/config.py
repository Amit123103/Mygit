import configparser
import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class ConfigManager:
    """Manages MyGit configuration across system, global, and repository levels."""

    def __init__(self, repo_dir: Optional[Path] = None):
        self.repo_dir = repo_dir
        self.global_config_path = self.get_global_config_path()
        self.local_config_path = (repo_dir / ".mygit" / "config") if repo_dir else None

    @staticmethod
    def get_global_config_path() -> Path:
        """Get the cross-platform path to global configuration."""
        if os.name == "nt":
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                return Path(user_profile) / ".mygitconfig"
        return Path.home() / ".mygitconfig"

    def _load_parser(self, path: Optional[Path]) -> configparser.ConfigParser:
        parser = configparser.ConfigParser(interpolation=None)
        if path and path.is_file():
            try:
                parser.read(path, encoding="utf-8")
            except Exception:
                pass
        return parser

    def _save_parser(self, parser: configparser.ConfigParser, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            parser.write(f)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get config value checking Local -> Global -> Default hierarchy.
        Key format: 'section.option' or 'section.subsection.option'
        """
        parts = key.split(".")
        if len(parts) < 2:
            return default

        section = ".".join(parts[:-1])
        option = parts[-1]

        # 1. Local
        if self.local_config_path and self.local_config_path.is_file():
            local_parser = self._load_parser(self.local_config_path)
            if local_parser.has_section(section) and local_parser.has_option(section, option):
                return local_parser.get(section, option)

        # 2. Global
        if self.global_config_path.is_file():
            global_parser = self._load_parser(self.global_config_path)
            if global_parser.has_section(section) and global_parser.has_option(section, option):
                return global_parser.get(section, option)

        return default

    def set(self, key: str, value: str, global_scope: bool = False):
        """Set config value in global or local configuration file."""
        parts = key.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid config key format '{key}'. Expected 'section.option'")

        section = ".".join(parts[:-1])
        option = parts[-1]

        target_path = self.global_config_path if global_scope else self.local_config_path
        if not target_path:
            raise ValueError("No local repository found to write local configuration.")

        parser = self._load_parser(target_path)
        if not parser.has_section(section):
            parser.add_section(section)

        parser.set(section, option, value)
        self._save_parser(parser, target_path)

    def unset(self, key: str, global_scope: bool = False):
        """Remove a config key."""
        parts = key.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid config key format '{key}'.")

        section = ".".join(parts[:-1])
        option = parts[-1]

        target_path = self.global_config_path if global_scope else self.local_config_path
        if not target_path or not target_path.is_file():
            return

        parser = self._load_parser(target_path)
        if parser.has_section(section) and parser.has_option(section, option):
            parser.remove_option(section, option)
            if len(parser.options(section)) == 0:
                parser.remove_section(section)
            self._save_parser(parser, target_path)

    def list_all(self) -> Dict[str, str]:
        """List all config options combined (Global overwritten by Local)."""
        return self.get_all_dict()

    def get_all_dict(self) -> Dict[str, str]:
        config_map: Dict[str, str] = {}

        # Load Global
        if self.global_config_path.is_file():
            g_parser = self._load_parser(self.global_config_path)
            for sec in g_parser.sections():
                for opt in g_parser.options(sec):
                    config_map[f"{sec}.{opt}"] = g_parser.get(sec, opt)

        # Load Local
        if self.local_config_path and self.local_config_path.is_file():
            l_parser = self._load_parser(self.local_config_path)
            for sec in l_parser.sections():
                for opt in l_parser.options(sec):
                    config_map[f"{sec}.{opt}"] = l_parser.get(sec, opt)

        return config_map

    def get_aliases(self) -> Dict[str, str]:
        """Returns a dict of configured aliases (key: alias name, value: command expansion)."""
        aliases = {}
        all_cfg = self.get_all_dict()
        for k, v in all_cfg.items():
            if k.startswith("alias."):
                alias_name = k[len("alias.") :]
                aliases[alias_name] = v
        return aliases
