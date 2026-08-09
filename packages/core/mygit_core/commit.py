import os
from typing import Dict, List, Optional, Tuple

from mygit_core.config import ConfigManager
from mygit_core.diff import compute_unified_diff, get_tree_files
from mygit_core.index import Index
from mygit_core.objects import Blob, Commit, ObjectStore
from mygit_core.repository import Repository


def get_author_info(repo: Repository) -> Tuple[str, str]:
    """Retrieves user.name and user.email from ConfigManager."""
    cfg = ConfigManager(repo.worktree)
    name = cfg.get("user.name") or os.environ.get("MYGIT_AUTHOR_NAME") or "Developer"
    email = cfg.get("user.email") or os.environ.get("MYGIT_AUTHOR_EMAIL") or "developer@example.com"
    return name, f"{name} <{email}>"


def create_commit(
    repo: Repository,
    message: str,
    parent_shas: Optional[List[str]] = None,
    author: Optional[str] = None,
    signature: Optional[str] = None,
) -> str:
    """
    Creates a new Commit object from current staging area index.
    Updates the current branch ref or HEAD pointer.
    Returns the created commit SHA-256 string.
    """
    index = Index(repo.index_file)
    if not index.entries:
        raise ValueError("Nothing staged to commit (use 'mygit add' to stage files).")

    object_store = ObjectStore(repo.objects_dir)

    # Write staged trees
    tree_sha = index.write_tree(object_store)

    # Determine parent commit(s)
    if parent_shas is None:
        parent_shas = []
        is_sym, head_val = repo.get_head_ref()
        current_commit = repo.resolve_ref(head_val)
        if current_commit:
            parent_shas.append(current_commit)

    if not author:
        _, author = get_author_info(repo)

    committer = author

    commit = Commit(
        tree_sha=tree_sha,
        parents=parent_shas,
        author=author,
        committer=committer,
        message=message,
        signature=signature,
    )

    commit_sha = object_store.write_object(commit)

    # Update branch ref or detached HEAD
    is_sym, head_val = repo.get_head_ref()
    if is_sym:
        branch_name = head_val.replace("refs/heads/", "")
        repo.set_branch_ref(branch_name, commit_sha)
    else:
        repo.set_head_ref(commit_sha, symbolic=False)

    return commit_sha


def get_commit_history(
    repo: Repository, start_sha: Optional[str] = None, limit: Optional[int] = None
) -> List[Tuple[str, Commit]]:
    """Traverses commit graph backwards starting from start_sha or current HEAD."""
    object_store = ObjectStore(repo.objects_dir)
    if not start_sha:
        start_sha = repo.resolve_ref("HEAD")

    if not start_sha:
        return []

    history: List[Tuple[str, Commit]] = []
    visited = set()
    queue = [start_sha]

    while queue and (limit is None or len(history) < limit):
        curr_sha = queue.pop(0)
        if curr_sha in visited:
            continue
        visited.add(curr_sha)

        try:
            type_name, data = object_store.read_object(curr_sha)
            if type_name == "commit":
                commit = Commit.parse_data(data)
                history.append((curr_sha, commit))
                for parent in commit.parents:
                    if parent not in visited:
                        queue.append(parent)
        except Exception:
            pass

    return history


def show_commit(repo: Repository, commit_sha: str) -> str:
    """Generates detailed text view of a commit and diff patch against parent."""
    object_store = ObjectStore(repo.objects_dir)
    type_name, data = object_store.read_object(commit_sha)
    if type_name != "commit":
        raise ValueError(f"Object {commit_sha} is not a commit.")

    commit = Commit.parse_data(data)

    output = []
    output.append(f"commit {commit_sha}")
    output.append(f"Author: {commit.author}")
    output.append(f"Date:   {commit.timestamp}")
    if commit.parents:
        output.append(f"Parents: {' '.join(commit.parents)}")
    output.append("")
    for msg_line in commit.message.splitlines():
        output.append(f"    {msg_line}")
    output.append("\n" + "-" * 50 + "\n")

    # Get diff vs parent commit tree
    curr_files = get_tree_files(object_store, commit.tree_sha)
    parent_files: Dict[str, str] = {}
    if commit.parents:
        try:
            _, p_data = object_store.read_object(commit.parents[0])
            p_commit = Commit.parse_data(p_data)
            parent_files = get_tree_files(object_store, p_commit.tree_sha)
        except Exception:
            pass

    all_paths = sorted(set(curr_files.keys()) | set(parent_files.keys()))
    for path in all_paths:
        p_sha = parent_files.get(path)
        c_sha = curr_files.get(path)

        p_text = ""
        c_text = ""

        if p_sha:
            try:
                _, b_data = object_store.read_object(p_sha)
                p_text = b_data.decode("utf-8", errors="replace")
            except Exception:
                pass

        if c_sha:
            try:
                _, b_data = object_store.read_object(c_sha)
                c_text = b_data.decode("utf-8", errors="replace")
            except Exception:
                pass

        if p_sha != c_sha:
            patch = compute_unified_diff(p_text, c_text, path, path)
            if patch:
                output.append(patch)

    return "\n".join(output)
