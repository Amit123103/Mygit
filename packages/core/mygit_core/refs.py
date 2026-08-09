import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mygit_core.diff import get_tree_files
from mygit_core.index import Index
from mygit_core.objects import ObjectStore, Tag
from mygit_core.repository import Repository


def list_branches(repo: Repository) -> List[Tuple[str, str, bool]]:
    """Returns list of (branch_name, commit_sha, is_current)."""
    current_branch = repo.get_current_branch()
    results = []

    if repo.heads_dir.is_dir():
        for f in repo.heads_dir.glob("*"):
            if f.is_file():
                b_name = f.name
                sha = f.read_text(encoding="utf-8").strip()
                is_curr = b_name == current_branch
                results.append((b_name, sha, is_curr))

    results.sort(key=lambda x: x[0])
    return results


def create_branch(repo: Repository, branch_name: str, start_point: Optional[str] = None):
    """Creates a new branch pointing to start_point or current HEAD."""
    if not start_point:
        start_point = repo.resolve_ref("HEAD")

    if not start_point:
        raise ValueError("Cannot create branch: No commits exist yet in repository.")

    branch_file = repo.heads_dir / branch_name
    if branch_file.exists():
        raise ValueError(f"Branch '{branch_name}' already exists.")

    repo.set_branch_ref(branch_name, start_point)


def delete_branch(repo: Repository, branch_name: str, force: bool = False):
    """Deletes a branch ref."""
    current = repo.get_current_branch()
    if current == branch_name:
        raise ValueError(f"Cannot delete currently checked out branch '{branch_name}'.")

    branch_file = repo.heads_dir / branch_name
    if not branch_file.is_file():
        raise ValueError(f"Branch '{branch_name}' not found.")

    branch_file.unlink()


def restore_worktree_to_commit(repo: Repository, commit_sha: str):
    """Updates index and working directory to match the commit tree."""
    object_store = ObjectStore(repo.objects_dir)
    _, c_bytes = object_store.read_object(commit_sha)
    from mygit_core.objects import Commit

    commit = Commit.parse_data(c_bytes)
    target_files = get_tree_files(object_store, commit.tree_sha)

    index = Index(repo.index_file)
    index.entries.clear()

    # Clear worktree files (preserving .mygit)
    for item in repo.worktree.glob("*"):
        if item.name == ".mygit":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # Write target files to worktree and populate index
    for rel_path, blob_sha in target_files.items():
        _, b_bytes = object_store.read_object(blob_sha)
        file_path = repo.worktree / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b_bytes)

        stat = file_path.stat()
        index.add(rel_path, blob_sha, stat.st_size, stat.st_mtime)

    index.write()


def switch_branch(repo: Repository, branch_name: str, create: bool = False):
    """Switch to a branch, optionally creating it first."""
    branch_file = repo.heads_dir / branch_name
    if not branch_file.is_file():
        if create:
            create_branch(repo, branch_name)
        else:
            raise ValueError(f"Branch '{branch_name}' does not exist.")

    commit_sha = branch_file.read_text(encoding="utf-8").strip()
    restore_worktree_to_commit(repo, commit_sha)
    repo.set_head_ref(branch_name, symbolic=True)


def checkout_commit(repo: Repository, commit_sha: str):
    """Checkout a specific commit (detached HEAD state)."""
    full_sha = repo.resolve_ref(commit_sha)
    if not full_sha:
        raise ValueError(f"Commit/Ref '{commit_sha}' not found.")

    restore_worktree_to_commit(repo, full_sha)
    repo.set_head_ref(full_sha, symbolic=False)


def list_tags(repo: Repository) -> List[Tuple[str, str]]:
    """Returns list of (tag_name, target_sha)."""
    tags = []
    if repo.tags_dir.is_dir():
        for f in repo.tags_dir.glob("*"):
            if f.is_file():
                sha = f.read_text(encoding="utf-8").strip()
                tags.append((f.name, sha))
    tags.sort(key=lambda x: x[0])
    return tags


def create_tag(
    repo: Repository,
    tag_name: str,
    target_ref: Optional[str] = None,
    message: Optional[str] = None,
    tagger: Optional[str] = None,
    signature: Optional[str] = None,
):
    """Create lightweight or annotated tag."""
    target_sha = repo.resolve_ref(target_ref or "HEAD")
    if not target_sha:
        raise ValueError(f"Invalid tag target '{target_ref}'.")

    tag_file = repo.tags_dir / tag_name
    if tag_file.exists():
        raise ValueError(f"Tag '{tag_name}' already exists.")

    if message:
        # Annotated Tag Object
        object_store = ObjectStore(repo.objects_dir)
        tag_obj = Tag(
            object_sha=target_sha,
            type_name="commit",
            name=tag_name,
            tagger=tagger or "Developer <developer@example.com>",
            message=message,
            signature=signature,
        )
        created_tag_sha = object_store.write_object(tag_obj)
        tag_file.write_text(f"{created_tag_sha}\n", encoding="utf-8")
    else:
        # Lightweight Tag
        tag_file.write_text(f"{target_sha}\n", encoding="utf-8")
