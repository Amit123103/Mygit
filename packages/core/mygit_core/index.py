import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mygit_core.objects import Blob, ObjectStore, Tree, TreeEntry


class IndexEntry:
    """Represents a single file entry in the staging area index."""

    def __init__(self, path: str, sha: str, size: int, mtime: float, mode: str = "100644"):
        self.path = path.replace("\\", "/")  # Standardize relative path
        self.sha = sha
        self.size = size
        self.mtime = mtime
        self.mode = mode

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha": self.sha,
            "size": self.size,
            "mtime": self.mtime,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexEntry":
        return cls(
            path=data["path"],
            sha=data["sha"],
            size=data["size"],
            mtime=data["mtime"],
            mode=data.get("mode", "100644"),
        )


class Index:
    """Manages the staging area (.mygit/index)."""

    def __init__(self, index_file: Path):
        self.index_file = index_file
        self.entries: Dict[str, IndexEntry] = {}
        self.read()

    def read(self):
        """Read index entries from disk."""
        self.entries.clear()
        if self.index_file.is_file() and self.index_file.stat().st_size > 0:
            try:
                content = self.index_file.read_text(encoding="utf-8")
                data = json.loads(content)
                for entry_dict in data.get("entries", []):
                    entry = IndexEntry.from_dict(entry_dict)
                    self.entries[entry.path] = entry
            except Exception:
                self.entries = {}

    def write(self):
        """Save index entries atomically to disk."""
        data = {"version": 1, "entries": [e.to_dict() for e in self.entries.values()]}
        content = json.dumps(data, indent=2)
        tmp_file = self.index_file.with_suffix(".tmp")
        tmp_file.write_text(content, encoding="utf-8")
        tmp_file.replace(self.index_file)

    def add(self, rel_path: str, sha: str, size: int, mtime: float, mode: str = "100644"):
        """Add or update a staged file entry."""
        norm_path = rel_path.replace("\\", "/")
        self.entries[norm_path] = IndexEntry(
            path=norm_path, sha=sha, size=size, mtime=mtime, mode=mode
        )

    def remove(self, rel_path: str):
        """Remove an entry from staging."""
        norm_path = rel_path.replace("\\", "/")
        if norm_path in self.entries:
            del self.entries[norm_path]

    def get(self, rel_path: str) -> Optional[IndexEntry]:
        norm_path = rel_path.replace("\\", "/")
        return self.entries.get(norm_path)

    def write_tree(self, object_store: ObjectStore) -> str:
        """
        Recursively converts current staged index entries into a tree hierarchy of Tree objects.
        Returns the root tree SHA-256 string.
        """

        # Group entries by directory hierarchy
        def _build_tree_recursive(path_prefix: str, entries_in_level: List[IndexEntry]) -> str:
            tree_entries: List[TreeEntry] = []

            # Direct files in this level
            subdirs: Dict[str, List[IndexEntry]] = {}

            for entry in entries_in_level:
                # Remaining path relative to path_prefix
                rel = entry.path[len(path_prefix) :].lstrip("/") if path_prefix else entry.path
                if "/" in rel:
                    subdir_name = rel.split("/")[0]
                    if subdir_name not in subdirs:
                        subdirs[subdir_name] = []
                    subdirs[subdir_name].append(entry)
                else:
                    tree_entries.append(
                        TreeEntry(
                            mode=entry.mode, type_name="blob", sha=entry.sha, name=rel
                        )
                    )

            # Process subdirectories
            for subdir_name, sub_entries in subdirs.items():
                next_prefix = f"{path_prefix}/{subdir_name}" if path_prefix else subdir_name
                sub_tree_sha = _build_tree_recursive(next_prefix, sub_entries)
                tree_entries.append(
                    TreeEntry(
                        mode="040000", type_name="tree", sha=sub_tree_sha, name=subdir_name
                    )
                )

            tree_obj = Tree(tree_entries)
            return object_store.write_object(tree_obj)

        return _build_tree_recursive("", list(self.entries.values()))
