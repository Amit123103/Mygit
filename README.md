<<<<<<< HEAD
# Mygit
=======
# MyGit — Independent Version Control System

**MyGit** is a complete, modern version-control ecosystem built from scratch.

> [!NOTE]
> MyGit is **not** a shell wrapper around Git. It features its own content-addressed object store, binary index, tree builder, commit graph engine, 3-way merge engine, wire protocol, FastAPI remote server, React web dashboard, provider integrations, secret detection, and Ed25519 signing mechanism.

## Features

- **Content-Addressed Storage**: SHA-256 object database with zlib compression (Blobs, Trees, Commits, Tags).
- **Index & Staging Area**: Efficient binary/JSON index tracking file paths, modes, modification timestamps, and content hashes.
- **Merge Engine**: 3-way merge algorithm with Lowest Common Ancestor (LCA) graph search and conflict marker generation.
- **Security & Integrity**: Integrated secret scanner, Ed25519 commit signing, and repository health check (`mygit fsck`).
- **Remote Ecosystem**: Independent MyGit wire protocol, FastAPI backend server with PostgreSQL support, and full-featured React web interface.
- **Provider Interfaces**: Modular integrations for GitHub, GitLab, and Hugging Face repositories.
- **Large File Storage (LFS)**: Built-in LFS pointer generation and resumable binary asset transfer.
- **AI-Assisted Workflow**: Opt-in commit message generator and PR code reviewer.

## Installation & Usage

```bash
# Clone and install in editable mode
pip install -e .

# Initialize a repository
mygit init

# Configure user details
mygit config --global user.name "Developer"
mygit config --global user.email "developer@example.com"

# Stage & Commit
mygit add .
mygit commit -m "Initial commit"

# View status & history
mygit status
mygit log
```

## Architecture Monorepo Layout

```text
mygit/
├── apps/
│   ├── cli/            # MyGit Typer CLI app
│   ├── server/         # FastAPI backend remote server
│   └── web/            # React + TypeScript + Vite + Tailwind dashboard
├── packages/
│   ├── core/           # MyGit core VCS engine (repo, objects, index, diff, merge, fsck)
│   ├── protocol/       # Custom MyGit remote wire protocol (v1)
│   ├── providers/      # GitHub, GitLab, Hugging Face integrations
│   ├── security/       # Ed25519 signing & secret scanning engine
│   └── sdk/            # Python SDK wrapper
└── tests/              # Unit, integration, security, and E2E test suite
```
>>>>>>> 5f7eb9b (Initial commit)
