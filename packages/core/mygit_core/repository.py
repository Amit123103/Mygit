import os
from pathlib import Path
from typing import Optional, Tuple


class Repository:
    """Represents a MyGit repository on disk."""

    def __init__(self, worktree: Path):
        self.worktree = worktree.resolve()
        self.mygit_dir = self.worktree / ".mygit"
        self.objects_dir = self.mygit_dir / "objects"
        self.refs_dir = self.mygit_dir / "refs"
        self.heads_dir = self.refs_dir / "heads"
        self.tags_dir = self.refs_dir / "tags"
        self.remotes_dir = self.refs_dir / "remotes"
        self.index_file = self.mygit_dir / "index"
        self.config_file = self.mygit_dir / "config"

    @classmethod
    def init(cls, path: Path, default_branch: str = "main") -> "Repository":
        """Initialize a new MyGit repository structure."""
        repo = cls(path)
        if repo.mygit_dir.exists():
            # If already initialized, return repo instance cleanly
            return repo

        repo.mygit_dir.mkdir(parents=True, exist_ok=True)
        repo.objects_dir.mkdir(parents=True, exist_ok=True)
        repo.heads_dir.mkdir(parents=True, exist_ok=True)
        repo.tags_dir.mkdir(parents=True, exist_ok=True)
        repo.remotes_dir.mkdir(parents=True, exist_ok=True)
        (repo.mygit_dir / "logs").mkdir(parents=True, exist_ok=True)
        (repo.mygit_dir / "hooks").mkdir(parents=True, exist_ok=True)

        # Set default HEAD
        head_file = repo.mygit_dir / "HEAD"
        head_file.write_text(f"ref: refs/heads/{default_branch}\n", encoding="utf-8")

        # Initialize config
        if not repo.config_file.exists():
            repo.config_file.write_text(
                f"[core]\n\trepositoryformatversion = 1\n\tfilemode = true\n\tbare = false\n[init]\n\tdefaultBranch = {default_branch}\n",
                encoding="utf-8",
            )

        # Initialize empty index if not exists
        if not repo.index_file.exists():
            repo.index_file.write_bytes(b"")

        return repo

    @classmethod
    def find(cls, path: Optional[Path] = None) -> Optional["Repository"]:
        """Find the root repository traversing up parent directories."""
        current = (path or Path.cwd()).resolve()
        while True:
            if (current / ".mygit").is_dir():
                return cls(current)
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def get_head_ref(self) -> Tuple[bool, str]:
        """
        Returns (is_symbolic, value).
        If symbolic: (True, 'refs/heads/main')
        If detached: (False, '<commit_hash>')
        """
        head_file = self.mygit_dir / "HEAD"
        if not head_file.exists():
            return True, "refs/heads/main"

        content = head_file.read_text(encoding="utf-8").strip()
        if content.startswith("ref: "):
            return True, content[5:].strip()
        return False, content

    def set_head_ref(self, target: str, symbolic: bool = True):
        """Set HEAD to a branch ref or commit hash."""
        head_file = self.mygit_dir / "HEAD"
        if symbolic:
            if not target.startswith("refs/"):
                target = f"refs/heads/{target}"
            head_file.write_text(f"ref: {target}\n", encoding="utf-8")
        else:
            head_file.write_text(f"{target}\n", encoding="utf-8")

    def get_current_branch(self) -> Optional[str]:
        """Returns current branch name or None if detached HEAD."""
        is_sym, target = self.get_head_ref()
        if is_sym and target.startswith("refs/heads/"):
            return target[len("refs/heads/") :]
        return None

    def resolve_ref(self, ref_name: str) -> Optional[str]:
        """Resolve a reference name (branch, tag, HEAD, hash) to a 64-char SHA-256 commit hash."""
        if len(ref_name) == 64:
            # Full 64-char hash
            return ref_name

        if ref_name == "HEAD":
            is_sym, target = self.get_head_ref()
            if is_sym:
                return self.resolve_ref(target)
            return target

        # Branch
        branch_file = self.heads_dir / ref_name
        if branch_file.is_file():
            return branch_file.read_text(encoding="utf-8").strip()

        # Tag
        tag_file = self.tags_dir / ref_name
        if tag_file.is_file():
            return tag_file.read_text(encoding="utf-8").strip()

        # Full ref path (refs/heads/main)
        ref_file = self.mygit_dir / ref_name
        if ref_file.is_file():
            return ref_file.read_text(encoding="utf-8").strip()

        # Short hash search
        if 4 <= len(ref_name) < 64:
            matches = []
            for subdir in self.objects_dir.glob("*"):
                if subdir.is_dir() and len(subdir.name) == 2:
                    for obj_file in subdir.glob("*"):
                        full_hash = subdir.name + obj_file.name
                        if full_hash.startswith(ref_name):
                            matches.append(full_hash)
            if len(matches) == 1:
                return matches[0]

        return None

    def set_branch_ref(self, branch_name: str, commit_hash: str):
        """Set a branch ref pointer to a commit hash."""
        branch_file = self.heads_dir / branch_name
        branch_file.parent.mkdir(parents=True, exist_ok=True)
        branch_file.write_text(f"{commit_hash}\n", encoding="utf-8")
