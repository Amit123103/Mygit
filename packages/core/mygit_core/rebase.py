from pathlib import Path
from typing import List, Optional

from mygit_core.commit import create_commit, get_commit_history
from mygit_core.merge import find_merge_base
from mygit_core.objects import Commit, ObjectStore
from mygit_core.refs import restore_worktree_to_commit
from mygit_core.repository import Repository


class RebaseEngine:

    def __init__(self, repo: Repository):
        self.repo = repo
        self.rebase_dir = repo.mygit_dir / "rebase-apply"
        self.head_name_file = self.rebase_dir / "head-name"
        self.onto_file = self.rebase_dir / "onto"
        self.orig_head_file = self.rebase_dir / "orig-head"

    def is_rebasing(self) -> bool:
        return self.rebase_dir.is_dir()

    def rebase(self, upstream_ref: str) -> str:
        if self.is_rebasing():
            raise ValueError(
                "Rebase already in progress! Use 'mygit rebase --continue' or 'mygit rebase --abort'."
            )

        head_sha = self.repo.resolve_ref("HEAD")
        upstream_sha = self.repo.resolve_ref(upstream_ref)

        if not head_sha or not upstream_sha:
            raise ValueError(f"Invalid rebase target '{upstream_ref}'.")

        base_sha = find_merge_base(self.repo, head_sha, upstream_sha)
        if base_sha == head_sha:
            return "Current branch is up to date."

        # Collect commits to replay (from base_sha up to head_sha)
        history = get_commit_history(self.repo, head_sha)
        replay_commits: List[Tuple[str, Commit]] = []

        for c_sha, commit in history:
            if c_sha == base_sha:
                break
            replay_commits.append((c_sha, commit))

        replay_commits.reverse()  # Replay in forward chronological order

        if not replay_commits:
            return "No commits to replay."

        # Save rebase state
        self.rebase_dir.mkdir(parents=True, exist_ok=True)
        curr_branch = self.repo.get_current_branch() or "HEAD"
        self.head_name_file.write_text(f"{curr_branch}\n", encoding="utf-8")
        self.onto_file.write_text(f"{upstream_sha}\n", encoding="utf-8")
        self.orig_head_file.write_text(f"{head_sha}\n", encoding="utf-8")

        # Fast replay if clean
        restore_worktree_to_commit(self.repo, upstream_sha)
        current_head = upstream_sha

        for old_sha, old_commit in replay_commits:
            # Replay commit content
            restore_worktree_to_commit(self.repo, old_commit.tree_sha)
            current_head = create_commit(
                self.repo,
                message=old_commit.message,
                parent_shas=[current_head],
                author=old_commit.author,
            )

        # Cleanup rebase directory
        import shutil

        shutil.rmtree(self.rebase_dir)

        return (
            f"Successfully rebased and updated {curr_branch} onto {upstream_ref} ({current_head[:7]})."
        )

    def abort(self) -> str:
        if not self.is_rebasing():
            raise ValueError("No rebase in progress to abort.")

        orig_sha = self.orig_head_file.read_text(encoding="utf-8").strip()
        branch_name = self.head_name_file.read_text(encoding="utf-8").strip()

        restore_worktree_to_commit(self.repo, orig_sha)
        if branch_name != "HEAD":
            self.repo.set_branch_ref(branch_name, orig_sha)
            self.repo.set_head_ref(branch_name, symbolic=True)
        else:
            self.repo.set_head_ref(orig_sha, symbolic=False)

        import shutil

        shutil.rmtree(self.rebase_dir)
        return "Rebase aborted."
