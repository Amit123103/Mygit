from pathlib import Path
from typing import Dict, List, Optional

from mygit_core.commit import create_commit, get_commit_history
from mygit_core.index import Index
from mygit_core.objects import Blob, ObjectStore
from mygit_core.refs import list_branches, switch_branch
from mygit_core.repository import Repository
from mygit_core.status import analyze_status


class RepositorySDK:
    """Python SDK interface for MyGit VCS engine."""

    def __init__(self, repo: Repository):
        self._repo = repo

    @classmethod
    def init(cls, path: str = ".") -> "RepositorySDK":
        repo = Repository.init(Path(path))
        return cls(repo)

    @classmethod
    def open(cls, path: str = ".") -> "RepositorySDK":
        repo = Repository.find(Path(path))
        if not repo:
            raise FileNotFoundError(f"No MyGit repository found at '{path}'")
        return cls(repo)

    def status(self) -> dict:
        return analyze_status(self._repo).to_dict()

    def add(self, rel_path: str):
        full_path = self._repo.worktree / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File '{rel_path}' does not exist.")

        data = full_path.read_bytes()
        blob = Blob.from_bytes(data)
        object_store = ObjectStore(self._repo.objects_dir)
        sha = object_store.write_object(blob)

        index = Index(self._repo.index_file)
        stat = full_path.stat()
        index.add(rel_path, sha, stat.st_size, stat.st_mtime)
        index.write()

    def commit(self, message: str, author: Optional[str] = None) -> str:
        return create_commit(self._repo, message=message, author=author)

    def log(self, limit: int = 10) -> List[dict]:
        history = get_commit_history(self._repo, limit=limit)
        return [
            {
                "commit_sha": sha,
                "author": c.author,
                "message": c.message,
                "timestamp": c.timestamp,
                "parents": c.parents,
            }
            for sha, c in history
        ]

    def list_branches(self) -> List[dict]:
        branches = list_branches(self._repo)
        return [
            {"name": name, "commit_sha": sha, "is_current": is_curr}
            for name, sha, is_curr in branches
        ]

    def switch(self, branch_name: str, create: bool = False):
        switch_branch(self._repo, branch_name, create=create)
