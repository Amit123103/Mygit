import tempfile
from pathlib import Path
from mygit_core.repository import Repository
from mygit_core.commit import create_commit, get_commit_history
from mygit_core.status import analyze_status
from mygit_core.refs import create_branch, switch_branch
from mygit_core.merge import MergeEngine
from mygit_core.fsck import run_fsck
from mygit_core.index import Index
from mygit_core.objects import Blob, ObjectStore


def test_full_repository_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        worktree = Path(tmp_dir)

        # 1. Init
        repo = Repository.init(worktree, default_branch="main")
        assert repo.mygit_dir.is_dir()

        # 2. Add file
        hello_file = worktree / "hello.txt"
        hello_file.write_text("Hello MyGit Engine\n", encoding="utf-8")

        index = Index(repo.index_file)
        object_store = ObjectStore(repo.objects_dir)
        blob = Blob.from_bytes(hello_file.read_bytes())
        sha = object_store.write_object(blob)
        stat = hello_file.stat()
        index.add("hello.txt", sha, stat.st_size, stat.st_mtime)
        index.write()

        # 3. Status check
        status_res = analyze_status(repo)
        assert "hello.txt" in status_res.staged_new

        # 4. Commit
        c1_sha = create_commit(repo, message="Initial commit")
        assert len(c1_sha) == 64

        history = get_commit_history(repo)
        assert len(history) == 1
        assert history[0][0] == c1_sha

        # 5. Branching & Merge
        create_branch(repo, "feature/login")
        switch_branch(repo, "feature/login")

        feat_file = worktree / "feature.txt"
        feat_file.write_text("Feature content\n", encoding="utf-8")
        blob2 = Blob.from_bytes(feat_file.read_bytes())
        sha2 = object_store.write_object(blob2)
        stat2 = feat_file.stat()
        index.add("feature.txt", sha2, stat2.st_size, stat2.st_mtime)
        index.write()

        c2_sha = create_commit(repo, message="Add feature")

        # Switch back to main and merge
        switch_branch(repo, "main")
        assert not (worktree / "feature.txt").exists()

        merge_engine = MergeEngine(repo)
        msg = merge_engine.merge("feature/login")
        assert (worktree / "feature.txt").exists()

        # 6. Repository Integrity check
        report = run_fsck(repo)
        assert not report.corrupt_objects
        assert not report.broken_refs
