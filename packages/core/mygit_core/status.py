import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

from mygit_core.diff import get_tree_files
from mygit_core.ignore import IgnoreMatcher
from mygit_core.index import Index
from mygit_core.objects import Blob, Commit, ObjectStore
from mygit_core.repository import Repository


class StatusResult:
    def __init__(self):
        self.branch: str = "main"
        self.detached: bool = False
        self.staged_new: List[str] = []
        self.staged_modified: List[str] = []
        self.staged_deleted: List[str] = []
        self.unstaged_modified: List[str] = []
        self.unstaged_deleted: List[str] = []
        self.untracked: List[str] = []
        self.ignored: List[str] = []

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "detached": self.detached,
            "staged": {
                "new": self.staged_new,
                "modified": self.staged_modified,
                "deleted": self.staged_deleted,
            },
            "unstaged": {
                "modified": self.unstaged_modified,
                "deleted": self.unstaged_deleted,
            },
            "untracked": self.untracked,
            "ignored": self.ignored,
        }


def analyze_status(repo: Repository) -> StatusResult:
    """Analyze working directory, index, and HEAD commit state."""
    result = StatusResult()
    ignore_matcher = IgnoreMatcher(repo.worktree)
    index = Index(repo.index_file)
    object_store = ObjectStore(repo.objects_dir)

    # 1. Branch/HEAD state
    is_sym, head_val = repo.get_head_ref()
    if is_sym:
        result.branch = head_val.replace("refs/heads/", "")
        head_commit_sha = repo.resolve_ref(head_val)
    else:
        result.branch = head_val[:7] if len(head_val) == 64 else head_val
        result.detached = True
        head_commit_sha = head_val

    # 2. Get HEAD tree files {path: blob_sha}
    head_files: Dict[str, str] = {}
    if head_commit_sha:
        try:
            _, commit_bytes = object_store.read_object(head_commit_sha)
            commit = Commit.parse_data(commit_bytes)
            head_files = get_tree_files(object_store, commit.tree_sha)
        except Exception:
            pass

    # 3. Compare Staged Index vs HEAD Commit
    index_files = set(index.entries.keys())
    head_file_set = set(head_files.keys())

    for path, entry in index.entries.items():
        if path not in head_files:
            result.staged_new.append(path)
        elif entry.sha != head_files[path]:
            result.staged_modified.append(path)

    for path in head_file_set - index_files:
        result.staged_deleted.append(path)

    # 4. Compare Working Directory vs Index
    worktree_files: Set[str] = set()
    for root, dirs, files in os.walk(repo.worktree):
        # Exclude .mygit directory
        if ".mygit" in dirs:
            dirs.remove(".mygit")

        rel_root = Path(root).relative_to(repo.worktree)
        rel_root_str = "" if rel_root == Path(".") else rel_root.as_posix()

        for file_name in files:
            rel_path = f"{rel_root_str}/{file_name}" if rel_root_str else file_name
            if ignore_matcher.is_ignored(rel_path):
                result.ignored.append(rel_path)
                continue

            worktree_files.add(rel_path)
            full_path = repo.worktree / rel_path

            if rel_path in index.entries:
                entry = index.entries[rel_path]
                # Check modification timestamp or size first for speed
                stat = full_path.stat()
                if stat.st_size != entry.size or abs(stat.st_mtime - entry.mtime) > 1e-4:
                    # Calculate content SHA to confirm modification
                    data = full_path.read_bytes()
                    blob = Blob.from_bytes(data)
                    if blob.compute_hash() != entry.sha:
                        result.unstaged_modified.append(rel_path)
            else:
                result.untracked.append(rel_path)

    # Detect deleted files in worktree
    for path in index_files:
        if path not in worktree_files and not ignore_matcher.is_ignored(path):
            if not (repo.worktree / path).exists():
                result.unstaged_deleted.append(path)

    # Sort results for deterministic output
    result.staged_new.sort()
    result.staged_modified.sort()
    result.staged_deleted.sort()
    result.unstaged_modified.sort()
    result.unstaged_deleted.sort()
    result.untracked.sort()
    result.ignored.sort()

    return result
