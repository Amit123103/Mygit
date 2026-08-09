from typing import Dict, List, Optional, Set, Tuple

from mygit_core.commit import create_commit
from mygit_core.diff import get_tree_files
from mygit_core.index import Index
from mygit_core.objects import Commit, ObjectStore
from mygit_core.refs import restore_worktree_to_commit
from mygit_core.repository import Repository


def find_merge_base(repo: Repository, commit_a: str, commit_b: str) -> Optional[str]:
    """Finds Lowest Common Ancestor (LCA) commit SHA between commit_a and commit_b."""
    object_store = ObjectStore(repo.objects_dir)

    def _get_ancestors(start_sha: str) -> Set[str]:
        ancestors = set()
        queue = [start_sha]
        while queue:
            curr = queue.pop(0)
            if curr in ancestors:
                continue
            ancestors.add(curr)
            try:
                _, data = object_store.read_object(curr)
                c = Commit.parse_data(data)
                for p in c.parents:
                    if p not in ancestors:
                        queue.append(p)
            except Exception:
                pass
        return ancestors

    anc_a = _get_ancestors(commit_a)

    # BFS from commit_b to find first ancestor present in anc_a
    queue = [commit_b]
    visited = set()
    while queue:
        curr = queue.pop(0)
        if curr in visited:
            continue
        visited.add(curr)
        if curr in anc_a:
            return curr
        try:
            _, data = object_store.read_object(curr)
            c = Commit.parse_data(data)
            for p in c.parents:
                if p not in visited:
                    queue.append(p)
        except Exception:
            pass

    return None


def merge_3way_file(base_text: str, ours_text: str, theirs_text: str) -> Tuple[bool, str]:
    """
    3-way merge on text file contents.
    Returns (has_conflict, merged_text_content).
    """
    if ours_text == theirs_text:
        return False, ours_text
    if ours_text == base_text:
        return False, theirs_text
    if theirs_text == base_text:
        return False, ours_text

    # Content changed on both branches differently -> potential conflict
    ours_lines = ours_text.splitlines(keepends=True)
    theirs_lines = theirs_text.splitlines(keepends=True)
    base_lines = base_text.splitlines(keepends=True)

    # Line-level 3-way diff simulation
    has_conflict = False
    result_lines = []

    # Simplified 3-way conflict block formatter
    result_lines.append("<<<<<<< OURS\n")
    result_lines.extend(ours_lines)
    result_lines.append("=======\n")
    result_lines.extend(theirs_lines)
    result_lines.append(">>>>>>> THEIRS\n")
    has_conflict = True

    return has_conflict, "".join(result_lines)


class MergeEngine:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.object_store = ObjectStore(repo.objects_dir)
        self.merge_head_file = repo.mygit_dir / "MERGE_HEAD"
        self.merge_msg_file = repo.mygit_dir / "MERGE_MSG"

    def is_merging(self) -> bool:
        return self.merge_head_file.is_file()

    def merge(self, target_branch_or_commit: str) -> str:
        """Perform branch merge into current branch."""
        if self.is_merging():
            raise ValueError("Merge already in progress! Use 'mygit merge --continue' or 'mygit merge --abort'.")

        ours_commit_sha = self.repo.resolve_ref("HEAD")
        theirs_commit_sha = self.repo.resolve_ref(target_branch_or_commit)

        if not ours_commit_sha or not theirs_commit_sha:
            raise ValueError(f"Invalid merge target '{target_branch_or_commit}'.")

        if ours_commit_sha == theirs_commit_sha:
            return "Already up to date."

        base_commit_sha = find_merge_base(self.repo, ours_commit_sha, theirs_commit_sha)

        # 1. Fast-forward merge check
        if base_commit_sha == ours_commit_sha:
            # Current branch is ancestor of target branch -> Fast-forward
            restore_worktree_to_commit(self.repo, theirs_commit_sha)
            current_branch = self.repo.get_current_branch()
            if current_branch:
                self.repo.set_branch_ref(current_branch, theirs_commit_sha)
            else:
                self.repo.set_head_ref(theirs_commit_sha, symbolic=False)
            return f"Fast-forward merge to {theirs_commit_sha[:7]}."

        # 2. 3-Way Merge
        base_files = get_tree_files(self.object_store, Commit.parse_data(self.object_store.read_object(base_commit_sha)[1]).tree_sha) if base_commit_sha else {}
        ours_files = get_tree_files(self.object_store, Commit.parse_data(self.object_store.read_object(ours_commit_sha)[1]).tree_sha)
        theirs_files = get_tree_files(self.object_store, Commit.parse_data(self.object_store.read_object(theirs_commit_sha)[1]).tree_sha)

        all_paths = sorted(set(base_files.keys()) | set(ours_files.keys()) | set(theirs_files.keys()))

        conflicts = []
        index = Index(self.repo.index_file)

        for path in all_paths:
            base_sha = base_files.get(path)
            ours_sha = ours_files.get(path)
            theirs_sha = theirs_files.get(path)

            base_txt = self.object_store.read_object(base_sha)[1].decode("utf-8", errors="replace") if base_sha else ""
            ours_txt = self.object_store.read_object(ours_sha)[1].decode("utf-8", errors="replace") if ours_sha else ""
            theirs_txt = self.object_store.read_object(theirs_sha)[1].decode("utf-8", errors="replace") if theirs_sha else ""

            has_conflict, merged_txt = merge_3way_file(base_txt, ours_txt, theirs_txt)

            file_path = self.repo.worktree / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(merged_txt, encoding="utf-8")

            if has_conflict:
                conflicts.append(path)
            else:
                # Stage clean auto-merged file
                from mygit_core.objects import Blob
                blob = Blob.from_bytes(merged_txt.encode("utf-8"))
                sha = self.object_store.write_object(blob)
                stat = file_path.stat()
                index.add(path, sha, stat.st_size, stat.st_mtime)

        index.write()

        if conflicts:
            # Save merge state for conflict resolution
            self.merge_head_file.write_text(f"{theirs_commit_sha}\n", encoding="utf-8")
            self.merge_msg_file.write_text(f"Merge branch '{target_branch_or_commit}'\n", encoding="utf-8")
            return f"CONFLICT (content): Merge conflict in {', '.join(conflicts)}. Resolve conflicts and run 'mygit merge --continue'."

        # No conflicts -> create merge commit automatically
        msg = f"Merge branch '{target_branch_or_commit}'"
        commit_sha = create_commit(self.repo, message=msg, parent_shas=[ours_commit_sha, theirs_commit_sha])
        return f"Merge made by 3-way strategy. Commit: {commit_sha[:7]}"

    def abort(self):
        """Abort merge and restore HEAD commit."""
        if not self.is_merging():
            raise ValueError("No merge in progress to abort.")

        head_sha = self.repo.resolve_ref("HEAD")
        if head_sha:
            restore_worktree_to_commit(self.repo, head_sha)

        if self.merge_head_file.exists():
            self.merge_head_file.unlink()
        if self.merge_msg_file.exists():
            self.merge_msg_file.unlink()

        return "Merge aborted cleanly."

    def continue_merge(self) -> str:
        """Complete merge after conflict resolution."""
        if not self.is_merging():
            raise ValueError("No merge in progress.")

        theirs_sha = self.merge_head_file.read_text(encoding="utf-8").strip()
        msg = self.merge_msg_file.read_text(encoding="utf-8").strip() if self.merge_msg_file.exists() else "Merge commit"
        ours_sha = self.repo.resolve_ref("HEAD")

        commit_sha = create_commit(self.repo, message=msg, parent_shas=[ours_sha, theirs_sha])

        if self.merge_head_file.exists():
            self.merge_head_file.unlink()
        if self.merge_msg_file.exists():
            self.merge_msg_file.unlink()

        return f"Merge resolved and committed: {commit_sha[:7]}"
