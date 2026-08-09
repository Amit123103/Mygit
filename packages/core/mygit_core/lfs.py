import hashlib
from pathlib import Path
from typing import List


class LFSManager:
    """Manages Large File Storage tracking and pointer generation."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir
        self.lfs_dir = repo_dir / ".mygit" / "lfs"
        self.lfs_objects_dir = self.lfs_dir / "objects"
        self.config_file = repo_dir / ".mygitlfsconfig"

    def track_pattern(self, pattern: str):
        """Track file pattern in .mygitlfsconfig."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if self.config_file.is_file():
            lines = self.config_file.read_text(encoding="utf-8").splitlines()

        if pattern not in lines:
            lines.append(pattern)
            self.config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def get_tracked_patterns(self) -> List[str]:
        if not self.config_file.is_file():
            return []
        return [
            line.strip()
            for line in self.config_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

    def create_pointer(self, file_path: Path) -> str:
        """Store large file in .mygit/lfs/objects and return LFS pointer content."""
        data = file_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)

        # Write to lfs storage
        lfs_path = self.lfs_objects_dir / sha256[:2] / sha256[2:4] / sha256
        lfs_path.parent.mkdir(parents=True, exist_ok=True)
        if not lfs_path.exists():
            lfs_path.write_bytes(data)

        pointer_text = (
            f"version https://mygit-lfs.v1\n"
            f"oid sha256:{sha256}\n"
            f"size {size}\n"
        )
        return pointer_text
