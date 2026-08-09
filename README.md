# MyGit — Independent Version Control System & Ecosystem

**MyGit** is a complete, production-grade, independent version-control platform designed and built from scratch.

> [!IMPORTANT]
> **MyGit is not a wrapper around Git.**
> It features its own SHA-256 content-addressed object store, custom binary staging index, 3-way LCA merge engine, linear commit rebase engine, Ed25519 commit signing, entropy secret scanner, LFS pointer engine, FastAPI remote server, and React web dashboard.

---

## Highlights & Features

- **Pure Engine**: Zero execution of external `git` CLI binaries. Every operation (`init`, `add`, `commit`, `status`, `diff`, `branch`, `merge`, `rebase`, `fsck`, `gc`) is implemented natively in Python.
- **SHA-256 Content-Addressed Storage**: Immutable Blob, Tree, Commit, and Tag objects hashed with SHA-256 and compressed with `zlib`.
- **Staging Index (`.mygit/index`)**: JSON/binary packed staging engine tracking file modes, timestamps, sizes, and blob hashes.
- **Advanced Merge & Rebase Engine**: 3-way merge algorithm utilizing Lowest Common Ancestor (LCA) graph search and conflict marker generation (`<<<<<<< OURS`, `=======`, `>>>>>>> THEIRS`).
- **Security & Secret Protection**: Built-in Ed25519 key generation for commit/tag signatures and entropy heuristics scanner to block accidental commits of API keys, AWS credentials, and private keys.
- **Remote Wire Protocol & FastAPI Server**: HTTP stream object negotiation protocol with role-based access control, JWT authentication, PRs, Issues, and Webhooks.
- **Provider Integrations**: Modular API connectors for GitHub, GitLab, and Hugging Face repositories (Models, Code, Datasets).
- **React Web Interface**: Modern glassmorphic dashboard for browsing repositories, commit history, branches, and FSCK health checks.
- **Python SDK**: Full programmatical access via `from mygit_sdk import RepositorySDK`.

---

## Installation

### 1. From PyPI (Standard Installation)

```bash
pip install mygit
```

### 2. From Source (Local Development)

```bash
# Clone the repository
git clone https://github.com/Amit123103/Mygit.git
cd Mygit

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

Verify the installation:

```bash
mygit doctor
```

---

## Complete CLI Command Reference

### Repository Initialization

```bash
# Initialize a new MyGit repository in the current directory
mygit init

# Initialize in a specific target directory with custom default branch
mygit init /path/to/project --initial-branch main
```

### Configuration Management

```bash
# Set global user credentials
mygit config --global user.name "Developer Name"
mygit config --global user.email "developer@example.com"

# Set local repository configuration
mygit config init.defaultBranch main

# List all combined configuration options
mygit config --list

# Unset a configuration option
mygit config --unset user.name --global
```

### Working Tree & Staging Area

```bash
# Check working tree and staging status
mygit status

# Output status in machine-readable JSON format for IDEs
mygit status --json

# Stage specific files or directories
mygit add hello.py src/

# Stage all modified and new files in the working directory
mygit add .
mygit add -A

# Unstage files from the index
mygit reset hello.py
```

### Commits & History

```bash
# Record staged changes with a commit message
mygit commit -m "Add authentication module"

# Record a cryptographically signed commit using Ed25519 private key
mygit commit -m "Signed release commit" --sign

# View chronological commit logs
mygit log

# Compact one-line log format
mygit log --oneline

# Limit commit log count
mygit log -n 5

# Show detailed commit metadata and unified patch diff
mygit show <commit-sha>
```

### Inspection & Diffs

```bash
# Show unstaged working directory changes vs staged index
mygit diff

# Show staged changes vs HEAD commit
mygit diff --staged

# Show summary of file insertions and deletions
mygit diff --stat
```

### Branching & References

```bash
# List all local branches (starred current branch)
mygit branch

# Create a new branch
mygit branch feature/login

# Delete a branch
mygit branch -d feature/login

# Switch to an existing branch
mygit switch main

# Create and switch to a new branch in one command
mygit switch -c feature/payments

# Checkout a specific commit (Detached HEAD state)
mygit checkout <commit-sha>
```

### Merge & Conflict Resolution

```bash
# Merge a target branch into the current branch (Supports Fast-Forward & 3-Way LCA Merge)
mygit merge feature/login

# Abort an in-progress merge and restore clean state
mygit merge --abort

# Continue and commit merge after manually resolving conflict markers
mygit merge --continue
```

### Rebase Engine

```bash
# Replay current branch commits on top of upstream branch
mygit rebase main

# Abort an in-progress rebase
mygit rebase --abort
```

### Tags & Release Management

```bash
# List all tags
mygit tag

# Create a lightweight tag
mygit tag v1.0.0

# Create an annotated tag with message
mygit tag v1.0.0 -m "Production Release v1.0.0"
```

### Security & Cryptography

```bash
# Generate a new Ed25519 signing keypair in .mygit/
mygit key generate

# Export public key for commit verification
mygit key export

# Scan repository for hardcoded API keys, tokens, and private credentials
mygit secrets scan
```

### Health, FSCK & Maintenance

```bash
# Perform full repository consistency & SHA-256 hash integrity check
mygit fsck

# Run garbage collection and prune unreachable dangling objects
mygit gc

# Run self-diagnostics on system environment & local repository
mygit doctor

# One-command quick publish (initializes, stages, and commits clean state)
mygit publish
```

### Large File Storage (LFS)

```bash
# Track binary files and model checkpoints with LFS pointers
mygit lfs track "*.pt"
mygit lfs track "*.safetensors"
```

### AI-Assisted Workflow (Opt-in)

```bash
# Generate AI commit message suggestion based on staged diff
mygit ai commit
```

---

## Python SDK Reference

You can interact with MyGit programmatically using the `mygit_sdk` package:

```python
from mygit_sdk import RepositorySDK

# Initialize or open a repository
repo = RepositorySDK.init("/path/to/project")

# Stage files
repo.add("hello.py")

# Create a commit
commit_sha = repo.commit("Add initial hello module", author="Developer <dev@example.com>")
print(f"Created commit: {commit_sha}")

# Get status
status = repo.status()
print("Staged new files:", status["staged"]["new"])

# List commit history
history = repo.log(limit=5)
for c in history:
    print(c["commit_sha"][:7], c["message"])

# Switch branch
repo.switch("feature/login", create=True)
```

---

## Running Remote Server Backend & Web Interface

### Launch Remote FastAPI Server

```bash
python -m mygit_server.main
# Server runs on http://localhost:8000
# OpenAPI Swagger Documentation available at http://localhost:8000/docs
```

### Launch React Web Dashboard

```bash
cd apps/web
npm install
npm run dev
# Dashboard opens on http://localhost:3000
```

---

## License

MIT License. Built independently as a version control system ecosystem.
