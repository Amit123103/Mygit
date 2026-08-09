from typing import Dict, List, Set, Tuple

from mygit_core.objects import Commit, ObjectCorruptException, ObjectStore, Tree
from mygit_core.repository import Repository


class FsckReport:

    def __init__(self):
        self.objects_checked: int = 0
        self.hashes_valid: int = 0
        self.corrupt_objects: List[Tuple[str, str]] = []
        self.dangling_objects: List[str] = []
        self.broken_refs: List[Tuple[str, str]] = []

    def to_summary(self) -> str:
        lines = ["Checking repository integrity...", ""]
        lines.append(f"✓ {self.objects_checked} objects checked")
        lines.append(f"✓ {self.hashes_valid} object hashes valid")
        if self.corrupt_objects:
            lines.append(f"❌ {len(self.corrupt_objects)} corrupt object(s) detected:")
            for sha, err in self.corrupt_objects:
                lines.append(f"   {sha}: {err}")
        else:
            lines.append("✓ All object hashes valid")

        if self.broken_refs:
            lines.append(f"❌ {len(self.broken_refs)} broken ref(s) detected:")
            for ref, sha in self.broken_refs:
                lines.append(f"   {ref} -> {sha}")
        else:
            lines.append("✓ References valid")

        if not self.corrupt_objects and not self.broken_refs:
            lines.append("✓ No repository corruption detected")

        return "\n".join(lines)


def run_fsck(repo: Repository) -> FsckReport:
    """Run full repository consistency check."""
    report = FsckReport()
    object_store = ObjectStore(repo.objects_dir)

    all_shas: Set[str] = set()

    # 1. Scan object store files
    if repo.objects_dir.is_dir():
        for subdir in repo.objects_dir.glob("*"):
            if subdir.is_dir() and len(subdir.name) == 2:
                for obj_file in subdir.glob("*"):
                    if not obj_file.name.endswith(".tmp"):
                        sha = subdir.name + obj_file.name
                        all_shas.add(sha)

    # 2. Check each object hash integrity
    for sha in all_shas:
        report.objects_checked += 1
        try:
            type_name, data = object_store.read_object(sha)
            report.hashes_valid += 1

            # Validate internal structure
            if type_name == "commit":
                commit = Commit.parse_data(data)
                if commit.tree_sha and commit.tree_sha not in all_shas:
                    report.corrupt_objects.append(
                        (sha, f"Missing tree object {commit.tree_sha}")
                    )
                for parent_sha in commit.parents:
                    if parent_sha not in all_shas:
                        report.corrupt_objects.append(
                            (sha, f"Missing parent commit {parent_sha}")
                        )
            elif type_name == "tree":
                tree = Tree.parse_data(data)
                for entry in tree.entries:
                    if entry.sha not in all_shas:
                        report.corrupt_objects.append(
                            (sha, f"Missing tree entry {entry.name} ({entry.sha})")
                        )

        except ObjectCorruptException as e:
            report.corrupt_objects.append((sha, str(e)))
        except Exception as e:
            report.corrupt_objects.append((sha, f"Read failure: {e}"))

    # 3. Check reference pointers

    if repo.heads_dir.is_dir():
        for f in repo.heads_dir.glob("*"):
            if f.is_file():
                sha = f.read_text(encoding="utf-8").strip()
                if sha not in all_shas:
                    report.broken_refs.append((f"refs/heads/{f.name}", sha))

    if repo.tags_dir.is_dir():
        for f in repo.tags_dir.glob("*"):
            if f.is_file():
                sha = f.read_text(encoding="utf-8").strip()
                if sha not in all_shas:
                    report.broken_refs.append((f"refs/tags/{f.name}", sha))

    return report
