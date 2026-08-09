# MyGit Architecture & Distributed Version Control Theory

## 1. Executive Summary & Design Vision

**MyGit** is an independent, content-addressed version control platform engineered from scratch. It provides robust state tracking, branching, 3-way graph merging, cryptographic verification, and remote synchronization without relying on any external Git binaries or wrappers.

---

## 2. Fundamental Computer Science Theory

### 2.1 Content-Addressed Storage (CAS)
In traditional file systems, data is retrieved by location (`/path/to/file.txt`). In MyGit, data is addressed strictly by its **cryptographic hash** derived directly from its raw content:

$$\text{Address} = H(\text{Header} \parallel \text{Payload})$$

Where $H$ is the SHA-256 cryptographic hash function, and $\parallel$ denotes concatenation.

#### Key Benefits of Content Addressing:
1. **Immutability**: An object cannot be altered without changing its SHA-256 address.
2. **Deduplication**: Identical content across different files or commits shares the exact same blob address in disk storage.
3. **Integrity Verification**: Corrupted data is instantly detected by recalculating the object's SHA-256 checksum and comparing it against its address.

---

### 2.2 The Commit Directed Acyclic Graph (DAG)

Version history in MyGit is modeled as a **Directed Acyclic Graph (DAG)** of immutable Commit objects.

```
       (Root)
      Commit 1 [5f91ac]
         │
         ▼
      Commit 2 [81f21a] (main)
        /   \
       /     \
      ▼       ▼
  Commit 3   Commit 4 (feature)
  [c83d91]   [a92e10]
       \     /
        ▼   ▼
      Commit 5 [Merge Commit]
```

- **Nodes**: Immutable Commit objects containing snapshot pointers (Tree SHA) and metadata.
- **Edges**: Directed parent links pointing backward in time from child commit to parent commit(s).
- **Acyclic Constraint**: Time moves strictly forward; a commit can never be its own ancestor.

---

## 3. Storage Hierarchy

```text
Working Directory (Editable files on disk)
       │
       ▼  mygit add
 Staging Area Index (.mygit/index - Metadata & Hash map)
       │
       ▼  mygit commit
 Object Database (.mygit/objects/ - Compressed Blobs, Trees, Commits)
       │
       ▼  mygit push
 Remote Server (.mygit wire protocol over HTTP/HTTPS)
```

1. **Working Tree**: The physical directory containing files actively edited by the developer.
2. **Index (Staging Area)**: A fast binary/JSON state cache recording file paths, modification times (`mtime`), sizes, and staged blob SHA-256 hashes.
3. **Object Store**: The persistent append-only database storing zlib-compressed objects under `.mygit/objects/xx/yyyy...`.
