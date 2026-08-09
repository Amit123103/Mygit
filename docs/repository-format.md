# MyGit Repository & Object Format Specification

## 1. On-Disk Directory Layout

When `mygit init` is executed, MyGit creates a `.mygit` hidden directory containing `HEAD`, `config`, `index`, `objects/`, `refs/`, `logs/`, and `hooks/`.

---

## 2. Object Format Specification

All MyGit objects stored in `.mygit/objects/` adhere to a uniform binary envelope before zlib compression:

$$\text{Envelope} = \texttt{<type>} \parallel \texttt{" "} \parallel \texttt{<size\_ascii>} \parallel \texttt{"\textbackslash 0"} \parallel \texttt{<payload\_bytes>}$$

### Object Header Fields:
- `type`: ASCII string representing object class (`blob`, `tree`, `commit`, `tag`).
- `size_ascii`: Decimal representation of payload byte length.
- `\0`: Null byte delimiter separating header from raw payload.

### Object Storage Path:
If an object's SHA-256 hash is `c83d91f82e70...`:
- Directory: `.mygit/objects/c8/`
- File: `3d91f82e70...`
- Storage: Compressed using Python `zlib.compress(envelope, level=6)`.

---

## 3. Object Types & Payload Specifications

### 3.1 Blob Object (`type: blob`)
Stores raw binary or text file contents without filename or permission metadata.

```text
blob 18\0Hello MyGit Engine
```

---

### 3.2 Tree Object (`type: tree`)
Represents directory structure. Entries are sorted lexicographically by name.

**Entry Format:**
$$\texttt{<mode> <type> <sha256> <name>\textbackslash n}$$

**Example Tree Payload:**
```text
100644 blob c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398 README.md
040000 tree a92e104f188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398 src
```

---

### 3.3 Commit Object (`type: commit`)
Represents a repository snapshot and contains pointer to root Tree SHA, parent commit SHAs, author, committer, timestamp, message, and optional signature.

**Example Commit Payload:**
```text
tree bdb69acad959818609e251778950f250d5d55b40977b8d6f3949da19bba81f7f
parent c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398
author Developer <developer@example.com> 1786263769
committer Developer <developer@example.com> 1786263769
gpgsig MEQCID... (Ed25519 Signature Base64)

Initial commit of MyGit core architecture
```

---

### 3.4 Tag Object (`type: tag`)
Annotated tag pointing to a commit or tree.

```text
object c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398
type commit
tag v1.0.0
tagger Developer <developer@example.com> 1786263769

Production Release v1.0.0
```
