import hashlib
import time
import zlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ObjectCorruptException(Exception):
    """Raised when an object fails hash validation or decompression."""

    pass


class GitObject(ABC):
    """Abstract base class for all MyGit content-addressed objects."""

    def __init__(self, data: bytes):
        self.data = data

    @property
    @abstractmethod
    def type_name(self) -> str:
        pass

    def serialize(self) -> bytes:
        """Returns header + data: format = '<type> <len>\0<data>'."""
        header = f"{self.type_name} {len(self.data)}\0".encode("utf-8")
        return header + self.data

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of serialized object."""
        return hashlib.sha256(self.serialize()).hexdigest()

    def write(self, repo_objects_dir: Path) -> str:
        """Write object to storage with SHA-256 deduplication and zlib compression."""
        sha = self.compute_hash()
        subdir = repo_objects_dir / sha[:2]
        obj_path = subdir / sha[2:]

        if not obj_path.exists():
            subdir.mkdir(parents=True, exist_ok=True)
            compressed = zlib.compress(self.serialize())
            # Atomic file creation
            tmp_path = obj_path.with_suffix(".tmp")
            tmp_path.write_bytes(compressed)
            tmp_path.replace(obj_path)

        return sha


class Blob(GitObject):
    """Stores raw file bytes."""

    @property
    def type_name(self) -> str:
        return "blob"

    @classmethod
    def from_bytes(cls, data: bytes) -> "Blob":
        return cls(data)


class TreeEntry:
    """Entry inside a Tree object."""

    def __init__(self, mode: str, type_name: str, sha: str, name: str):
        self.mode = mode  # e.g., "100644" for file, "040000" for dir, "100755" for executable
        self.type_name = type_name  # "blob" or "tree"
        self.sha = sha  # 64-character SHA-256 string
        self.name = name

    def serialize(self) -> bytes:
        # Deterministic line format: "<mode> <type> <sha> <name>\n"
        return f"{self.mode} {self.type_name} {self.sha} {self.name}\n".encode("utf-8")

    @classmethod
    def parse(cls, line: str) -> "TreeEntry":
        parts = line.strip().split(" ", 3)
        if len(parts) != 4:
            raise ValueError(f"Invalid tree entry line: '{line}'")
        return cls(mode=parts[0], type_name=parts[1], sha=parts[2], name=parts[3])


class Tree(GitObject):
    """Stores directory structure entries."""

    def __init__(self, entries: List[TreeEntry]):
        self.entries = sorted(entries, key=lambda e: e.name)
        data = b"".join(e.serialize() for e in self.entries)
        super().__init__(data)

    @property
    def type_name(self) -> str:
        return "tree"

    @classmethod
    def parse_data(cls, data: bytes) -> "Tree":
        entries = []
        lines = data.decode("utf-8", errors="replace").splitlines()
        for line in lines:
            if line.strip():
                entries.append(TreeEntry.parse(line))
        return cls(entries)


class Commit(GitObject):
    """Stores commit metadata, parent links, author, committer, and tree ID."""

    def __init__(
        self,
        tree_sha: str,
        parents: List[str],
        author: str,
        committer: str,
        message: str,
        timestamp: Optional[int] = None,
        signature: Optional[str] = None,
    ):
        self.tree_sha = tree_sha
        self.parents = parents
        self.author = author
        self.committer = committer
        self.message = message
        self.timestamp = timestamp or int(time.time())
        self.signature = signature

        # Format commit content text
        lines = [f"tree {tree_sha}"]
        for p in parents:
            lines.append(f"parent {p}")
        lines.append(f"author {author} {self.timestamp}")
        lines.append(f"committer {committer} {self.timestamp}")
        if signature:
            lines.append(f"gpgsig {signature}")
        lines.append("")
        lines.append(message)

        super().__init__("\n".join(lines).encode("utf-8"))

    @property
    def type_name(self) -> str:
        return "commit"

    @classmethod
    def parse_data(cls, data: bytes) -> "Commit":
        text = data.decode("utf-8", errors="replace")
        header_part, _, message = text.partition("\n\n")

        tree_sha = ""
        parents = []
        author = ""
        committer = ""
        timestamp = 0
        signature = None

        sig_lines = []
        in_sig = False

        for line in header_part.splitlines():
            if line.startswith("gpgsig "):
                in_sig = True
                sig_lines.append(line[7:])
            elif in_sig:
                if line.startswith(" "):
                    sig_lines.append(line[1:])
                else:
                    in_sig = False

            if not in_sig:
                if line.startswith("tree "):
                    tree_sha = line[5:].strip()
                elif line.startswith("parent "):
                    parents.append(line[7:].strip())
                elif line.startswith("author "):
                    parts = line[7:].rsplit(" ", 1)
                    author = parts[0]
                    if len(parts) > 1 and parts[1].isdigit():
                        timestamp = int(parts[1])
                elif line.startswith("committer "):
                    parts = line[10:].rsplit(" ", 1)
                    committer = parts[0]

        if sig_lines:
            signature = "\n".join(sig_lines)

        return cls(
            tree_sha=tree_sha,
            parents=parents,
            author=author,
            committer=committer,
            message=message,
            timestamp=timestamp,
            signature=signature,
        )


class Tag(GitObject):
    """Stores annotated tag object."""

    def __init__(
        self,
        object_sha: str,
        type_name: str,
        name: str,
        tagger: str,
        message: str,
        timestamp: Optional[int] = None,
        signature: Optional[str] = None,
    ):
        self.object_sha = object_sha
        self.target_type = type_name
        self.tag_name = name
        self.tagger = tagger
        self.message = message
        self.timestamp = timestamp or int(time.time())
        self.signature = signature

        lines = [
            f"object {object_sha}",
            f"type {type_name}",
            f"tag {name}",
            f"tagger {tagger} {self.timestamp}",
        ]
        if signature:
            lines.append(f"gpgsig {signature}")
        lines.append("")
        lines.append(message)

        super().__init__("\n".join(lines).encode("utf-8"))

    @property
    def type_name(self) -> str:
        return "tag"


class ObjectStore:
    """Reads and writes objects to `.mygit/objects/` with SHA-256 verification."""

    def __init__(self, objects_dir: Path):
        self.objects_dir = objects_dir

    def read_object(self, sha: str) -> Tuple[str, bytes]:
        """Reads object by SHA-256 hash. Returns (type_name, payload_data)."""
        if len(sha) < 4:
            raise ValueError(f"Invalid SHA hash: {sha}")

        obj_path = self.objects_dir / sha[:2] / sha[2:]
        if not obj_path.is_file():
            raise FileNotFoundError(f"Object {sha} not found in object database.")

        compressed = obj_path.read_bytes()
        try:
            decompressed = zlib.decompress(compressed)
        except Exception as e:
            raise ObjectCorruptException(f"Decompression failed for object {sha}: {e}")

        # Validate header
        null_idx = decompressed.find(b"\0")
        if null_idx == -1:
            raise ObjectCorruptException(f"Invalid header format in object {sha}")

        header = decompressed[:null_idx].decode("utf-8")
        data = decompressed[null_idx + 1 :]

        type_name, size_str = header.split(" ")
        if int(size_str) != len(data):
            raise ObjectCorruptException(f"Object size mismatch for {sha}: expected {size_str}, got {len(data)}")

        # Verify Hash Integrity
        actual_hash = hashlib.sha256(decompressed).hexdigest()
        if actual_hash != sha:
            raise ObjectCorruptException(f"Hash integrity mismatch for object {sha}: computed {actual_hash}")

        return type_name, data

    def write_object(self, obj: GitObject) -> str:
        """Persist object to disk."""
        return obj.write(self.objects_dir)
