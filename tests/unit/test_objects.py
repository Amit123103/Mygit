import pytest
from pathlib import Path
import tempfile
from mygit_core.objects import Blob, Tree, TreeEntry, Commit, Tag, ObjectStore, ObjectCorruptException


def test_blob_creation_and_hash():
    content = b"Hello MyGit Engine"
    blob = Blob.from_bytes(content)
    sha = blob.compute_hash()
    assert len(sha) == 64  # SHA-256 hex string length


def test_object_store_write_and_read():
    with tempfile.TemporaryDirectory() as tmp_dir:
        obj_dir = Path(tmp_dir) / "objects"
        store = ObjectStore(obj_dir)

        blob = Blob.from_bytes(b"Content test")
        sha = store.write_object(blob)

        type_name, data = store.read_object(sha)
        assert type_name == "blob"
        assert data == b"Content test"


def test_tree_serialization():
    entry = TreeEntry(mode="100644", type_name="blob", sha="a" * 64, name="app.py")
    tree = Tree([entry])
    assert b"100644 blob " + ("a" * 64).encode("utf-8") + b" app.py\n" in tree.data


def test_commit_object():
    commit = Commit(
        tree_sha="b" * 64,
        parents=[],
        author="Developer <dev@example.com>",
        committer="Developer <dev@example.com>",
        message="Initial commit",
        timestamp=1600000000,
    )
    sha = commit.compute_hash()
    assert len(sha) == 64
    assert b"tree " + ("b" * 64).encode("utf-8") in commit.data
