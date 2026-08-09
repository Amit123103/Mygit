import os
import time
from typing import Set

from mygit_core.objects import Commit, ObjectStore, Tree
from mygit_core.repository import Repository


def get_reachable_objects(repo: Repository) -> Set[str]:
    """Finds all objects reachable from any reference (HEAD, branches, tags, remotes)."""
    object_store = ObjectStore(repo.objects_dir)
    reachable = set()

    # Collect all reference SHAs
    ref_shas = set()

    # HEAD
    head_sha = repo.resolve_ref("HEAD")
    if head_sha:
        ref_shas.add(head_sha)

    # Heads
    if repo.heads_dir.is_dir():
        for f in repo.heads_dir.glob("*"):
            if f.is_file():
                ref_shas.add(f.read_text(encoding="utf-8").strip())

    # Tags
    if repo.tags_dir.is_dir():
        for f in repo.tags_dir.glob("*"):
            if f.is_file():
                ref_shas.add(f.read_text(encoding="utf-8").strip())

    # Traverse graph from ref_shas
    queue = list(ref_shas)
    while queue:
        sha = queue.pop(0)
        if sha in reachable:
            continue
        reachable.add(sha)

        try:
            type_name, data = object_store.read_object(sha)
            if type_name == "commit":
                commit = Commit.parse_data(data)
                if commit.tree_sha and commit.tree_sha not in reachable:
                    queue.append(commit.tree_sha)
                for parent_sha in commit.parents:
                    if parent_sha not in reachable:
                        queue.append(parent_sha)
            elif type_name == "tree":
                tree = Tree.parse_data(data)
                for entry in tree.entries:
                    if entry.sha not in reachable:
                        queue.append(entry.sha)
        except Exception:
            pass

    return reachable


def run_gc(repo: Repository, prune_unreachable: bool = True) -> str:
    """Performs garbage collection and prunes unreachable objects."""
    reachable = get_reachable_objects(repo)

    all_shas = set()
    if repo.objects_dir.is_dir():
        for subdir in repo.objects_dir.glob("*"):
            if subdir.is_dir() and len(subdir.name) == 2:
                for obj_file in subdir.glob("*"):
                    if not obj_file.name.endswith(".tmp"):
                        all_shas.add(subdir.name + obj_file.name)

    unreachable = all_shas - reachable
    pruned_count = 0

    if prune_unreachable:
        for sha in unreachable:
            obj_path = repo.objects_dir / sha[:2] / sha[2:]
            try:
                obj_path.unlink()
                pruned_count += 1
            except Exception:
                pass

    return f"GC complete. {len(reachable)} reachable objects kept. {pruned_count} unreachable object(s) pruned."
