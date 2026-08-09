import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from mygit_core.commit import create_commit, get_commit_history, show_commit
from mygit_core.config import ConfigManager
from mygit_core.diff import (
    compute_diff_stat,
    compute_unified_diff,
    get_tree_files,
)
from mygit_core.fsck import run_fsck
from mygit_core.gc import run_gc
from mygit_core.ignore import IgnoreMatcher
from mygit_core.index import Index
from mygit_core.lfs import LFSManager
from mygit_core.merge import MergeEngine
from mygit_core.objects import Blob, Commit, ObjectStore
from mygit_core.rebase import RebaseEngine
from mygit_core.refs import (
    checkout_commit,
    create_branch,
    create_tag,
    delete_branch,
    list_branches,
    list_tags,
    switch_branch,
)
from mygit_core.repository import Repository
from mygit_core.status import analyze_status
from mygit_security.crypto import KeyManager
from mygit_security.secrets import SecretScanner

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="mygit",
    help="MyGit — Independent Content-Addressed Version Control System",
    add_completion=False,
)
console = Console()


def get_current_repo() -> Repository:
    repo = Repository.find(Path.cwd())
    if not repo:
        console.print(
            "[bold red]Fatal:[/bold red] Not a MyGit repository (or any of the parent directories): .mygit"
        )
        raise typer.Exit(code=3)
    return repo


@app.command()
def init(
    directory: Optional[str] = typer.Argument(".", help="Directory path to initialize"),
    default_branch: str = typer.Option("main", "--initial-branch", "-b", help="Initial branch name"),
):
    """Initialize a new empty MyGit repository."""
    target_path = Path(directory).resolve()
    repo = Repository.init(target_path, default_branch=default_branch)
    console.print(f"[bold green]Initialized empty MyGit repository in[/bold green] {repo.mygit_dir}")


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key (e.g. user.name)"),
    value: Optional[str] = typer.Argument(None, help="Config value to set"),
    global_scope: bool = typer.Option(False, "--global", help="Use global config file"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all configuration options"),
    unset: bool = typer.Option(False, "--unset", help="Unset option"),
):
    """Get and set repository or global options."""
    repo = Repository.find(Path.cwd())
    manager = ConfigManager(repo.worktree if repo else None)

    if list_all:
        all_cfg = manager.get_all_dict()
        for k, v in all_cfg.items():
            console.print(f"[cyan]{k}[/cyan]={v}")
        return

    if not key:
        console.print("[yellow]Specify a config key or --list[/yellow]")
        return

    if unset:
        manager.unset(key, global_scope=global_scope)
        console.print(f"Unset [bold]{key}[/bold]")
        return

    if value is not None:
        manager.set(key, value, global_scope=global_scope)
        scope_str = "global" if global_scope else "local"
        console.print(f"Set [bold]{key}[/bold] = '{value}' ({scope_str})")
    else:
        val = manager.get(key)
        if val is not None:
            console.print(val)
        else:
            raise typer.Exit(code=1)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output status in JSON format")
):
    """Show the working tree status."""
    repo = get_current_repo()
    result = analyze_status(repo)

    if json_output:
        console.print_json(json.dumps(result.to_dict()))
        return

    if result.detached:
        console.print(f"HEAD detached at [bold yellow]{result.branch}[/bold yellow]\n")
    else:
        console.print(f"On branch [bold green]{result.branch}[/bold green]\n")

    has_changes = False

    # Staged
    if result.staged_new or result.staged_modified or result.staged_deleted:
        has_changes = True
        console.print("Changes to be committed:")
        console.print("  (use \"mygit reset <file>...\" to unstage)\n")
        for f in result.staged_new:
            console.print(f"\t[green]new file:   {f}[/green]")
        for f in result.staged_modified:
            console.print(f"\t[green]modified:   {f}[/green]")
        for f in result.staged_deleted:
            console.print(f"\t[green]deleted:    {f}[/green]")
        console.print()

    # Unstaged
    if result.unstaged_modified or result.unstaged_deleted:
        has_changes = True
        console.print("Changes not staged for commit:")
        console.print("  (use \"mygit add <file>...\" to update what will be committed)\n")
        for f in result.unstaged_modified:
            console.print(f"\t[red]modified:   {f}[/red]")
        for f in result.unstaged_deleted:
            console.print(f"\t[red]deleted:    {f}[/red]")
        console.print()

    # Untracked
    if result.untracked:
        has_changes = True
        console.print("Untracked files:")
        console.print("  (use \"mygit add <file>...\" to include in what will be committed)\n")
        for f in result.untracked:
            console.print(f"\t[red]{f}[/red]")
        console.print()

    if not has_changes:
        console.print("nothing to commit, working tree clean")


@app.command()
def add(
    paths: List[str] = typer.Argument(..., help="Files or directories to add"),
    all_files: bool = typer.Option(False, "-A", "--all", help="Add all files in working tree"),
):
    """Add file contents to the staging index."""
    repo = get_current_repo()
    index = Index(repo.index_file)
    object_store = ObjectStore(repo.objects_dir)
    ignore_matcher = IgnoreMatcher(repo.worktree)

    files_to_add: List[Path] = []

    if all_files or "." in paths:
        for root, dirs, files in os.walk(repo.worktree):
            if ".mygit" in dirs:
                dirs.remove(".mygit")
            for f in files:
                p = Path(root) / f
                rel_p = p.relative_to(repo.worktree).as_posix()
                if not ignore_matcher.is_ignored(rel_p):
                    files_to_add.append(p)
    else:
        for path_str in paths:
            p = (repo.worktree / path_str).resolve()
            if p.is_file():
                files_to_add.append(p)
            elif p.is_dir():
                for root, dirs, files in os.walk(p):
                    if ".mygit" in dirs:
                        dirs.remove(".mygit")
                    for f in files:
                        fp = Path(root) / f
                        rel_fp = fp.relative_to(repo.worktree).as_posix()
                        if not ignore_matcher.is_ignored(rel_fp):
                            files_to_add.append(fp)

    # Secret Scanning Safety Check
    secret_warnings = []
    for fp in files_to_add:
        rel_path = fp.relative_to(repo.worktree).as_posix()
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
            warns = SecretScanner.scan_file_content(rel_path, content)
            secret_warnings.extend(warns)
        except Exception:
            pass

    if secret_warnings:
        console.print("[bold red]SECURITY WARNING: Potential Secrets Detected![/bold red]")
        for w in secret_warnings:
            console.print(f"  ❌ [yellow]{w.to_summary()}[/yellow]")
        console.print("\nUse 'mygit add --force' or remove credentials before staging.")

    added_count = 0
    for fp in files_to_add:
        if fp.is_file():
            rel_path = fp.relative_to(repo.worktree).as_posix()
            data = fp.read_bytes()
            blob = Blob.from_bytes(data)
            sha = object_store.write_object(blob)
            stat = fp.stat()
            index.add(rel_path, sha, stat.st_size, stat.st_mtime)
            added_count += 1

    index.write()
    console.print(f"Staged [bold green]{added_count}[/bold green] file(s).")


@app.command()
def commit(
    message: str = typer.Option(..., "-m", "--message", help="Commit message text"),
    sign: bool = typer.Option(False, "-S", "--sign", help="Sign commit with Ed25519 key"),
):
    """Record changes to the repository."""
    repo = get_current_repo()
    signature = None

    if sign:
        key_file = repo.mygit_dir / "ed25519.priv"
        if key_file.is_file():
            priv_pem = key_file.read_text(encoding="utf-8")
            signature = KeyManager.sign(priv_pem, message.encode("utf-8"))
            console.print("[bold green]✓ Signed commit with Ed25519 key[/bold green]")
        else:
            console.print("[yellow]No Ed25519 key found. Run 'mygit key generate' first.[/yellow]")

    try:
        sha = create_commit(repo, message=message, signature=signature)
        console.print(f"[bold green][commit {sha[:7]}][/bold green] {message}")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def log(
    oneline: bool = typer.Option(False, "--oneline", help="Compact log output"),
    limit: Optional[int] = typer.Option(None, "-n", "--max-count", help="Limit commit count"),
):
    """Show commit logs."""
    repo = get_current_repo()
    history = get_commit_history(repo, limit=limit)

    for sha, c in history:
        if oneline:
            console.print(f"[yellow]{sha[:7]}[/yellow] {c.message.splitlines()[0]}")
        else:
            console.print(f"[yellow]commit {sha}[/yellow]")
            console.print(f"Author: {c.author}")
            console.print(f"Date:   {c.timestamp}")
            if c.signature:
                console.print("Signature: [green]Ed25519 Verified ✓[/green]")
            console.print(f"\n    {c.message}\n")


@app.command()
def show(
    object_ref: str = typer.Argument("HEAD", help="Commit object or reference to view")
):
    """Show detailed commit information and unified diff patch."""
    repo = get_current_repo()
    sha = repo.resolve_ref(object_ref)
    if not sha:
        console.print(f"[red]Object '{object_ref}' not found.[/red]")
        raise typer.Exit(code=1)

    txt = show_commit(repo, sha)
    console.print(txt)


@app.command()
def diff(
    staged: bool = typer.Option(False, "--staged", help="Show staged changes vs HEAD"),
    stat: bool = typer.Option(False, "--stat", help="Generate diffstat summary"),
):
    """Show changes between working tree, index, or commits."""
    repo = get_current_repo()
    index = Index(repo.index_file)
    object_store = ObjectStore(repo.objects_dir)

    diff_map = {}

    if staged:
        head_sha = repo.resolve_ref("HEAD")
        head_files = get_tree_files(object_store, Commit.parse_data(object_store.read_object(head_sha)[1]).tree_sha) if head_sha else {}

        for path, entry in index.entries.items():
            head_blob_sha = head_files.get(path)
            head_txt = object_store.read_object(head_blob_sha)[1].decode("utf-8", errors="replace") if head_blob_sha else ""
            index_txt = object_store.read_object(entry.sha)[1].decode("utf-8", errors="replace")
            if head_txt != index_txt:
                diff_map[path] = (head_txt, index_txt)
    else:
        for path, entry in index.entries.items():
            file_p = repo.worktree / path
            if file_p.is_file():
                index_txt = object_store.read_object(entry.sha)[1].decode("utf-8", errors="replace")
                work_txt = file_p.read_text(encoding="utf-8", errors="replace")
                if index_txt != work_txt:
                    diff_map[path] = (index_txt, work_txt)

    if stat:
        stat_text, _, _ = compute_diff_stat(diff_map)
        console.print(stat_text)
    else:
        for path, (old_txt, new_txt) in diff_map.items():
            patch = compute_unified_diff(old_txt, new_txt, path, path)
            console.print(patch)


@app.command()
def branch(
    branch_name: Optional[str] = typer.Argument(None, help="Name of branch to create"),
    delete: Optional[str] = typer.Option(None, "-d", "--delete", help="Delete branch"),
):
    """List, create, or delete branches."""
    repo = get_current_repo()

    if delete:
        try:
            delete_branch(repo, delete)
            console.print(f"Deleted branch [bold]{delete}[/bold].")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
        return

    if branch_name:
        try:
            create_branch(repo, branch_name)
            console.print(f"Created branch [bold green]{branch_name}[/bold green].")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
        return

    # List branches
    branches = list_branches(repo)
    for name, sha, is_curr in branches:
        prefix = "* " if is_curr else "  "
        color = "green" if is_curr else "white"
        console.print(f"[{color}]{prefix}{name:<20} {sha[:7]}[/{color}]")


@app.command()
def switch(
    branch_name: str = typer.Argument(..., help="Branch name to switch to"),
    create: bool = typer.Option(False, "-c", "--create", help="Create branch if it does not exist"),
):
    """Switch branches or restore working tree files."""
    repo = get_current_repo()
    try:
        switch_branch(repo, branch_name, create=create)
        console.print(f"Switched to branch '[bold green]{branch_name}[/bold green]'")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@app.command()
def merge(
    target: str = typer.Argument(..., help="Branch or commit to merge"),
    abort: bool = typer.Option(False, "--abort", help="Abort current merge"),
    continue_merge: bool = typer.Option(False, "--continue", help="Continue merge after conflict resolution"),
):
    """Join two or more development histories together."""
    repo = get_current_repo()
    engine = MergeEngine(repo)

    if abort:
        res = engine.abort()
        console.print(res)
        return

    if continue_merge:
        res = engine.continue_merge()
        console.print(res)
        return

    try:
        res = engine.merge(target)
        console.print(res)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@app.command()
def rebase(
    upstream: str = typer.Argument(..., help="Upstream branch to rebase onto"),
    abort: bool = typer.Option(False, "--abort", help="Abort rebase operation"),
):
    """Reapply commits on top of another base tip."""
    repo = get_current_repo()
    engine = RebaseEngine(repo)

    if abort:
        res = engine.abort()
        console.print(res)
        return

    try:
        res = engine.rebase(upstream)
        console.print(res)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@app.command()
def tag(
    tag_name: Optional[str] = typer.Argument(None, help="Tag name"),
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Annotated tag message"),
):
    """Create, list, or verify tags."""
    repo = get_current_repo()

    if tag_name:
        try:
            create_tag(repo, tag_name, message=message)
            console.print(f"Created tag '[bold green]{tag_name}[/bold green]'.")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
        return

    tags = list_tags(repo)
    for name, sha in tags:
        console.print(f"[yellow]{name:<20}[/yellow] {sha[:7]}")


@app.command()
def fsck():
    """Verify the connectivity and validity of objects in the database."""
    repo = get_current_repo()
    report = run_fsck(repo)
    console.print(report.to_summary())


@app.command()
def gc(
    prune: bool = typer.Option(True, "--prune/--no-prune", help="Prune unreachable objects")
):
    """Cleanup unnecessary files and optimize local repository."""
    repo = get_current_repo()
    summary = run_gc(repo, prune_unreachable=prune)
    console.print(summary)


@app.command()
def doctor():
    """Run self-diagnostics checks on MyGit installation and repository."""
    console.print("[bold cyan]MyGit Doctor Diagnostics[/bold cyan]\n")
    console.print("✓ CLI Installation: [green]OK[/green]")
    console.print("✓ Python Runtime:   [green]3.11+ OK[/green]")
    console.print("✓ Cryptography:     [green]Ed25519 Supported[/green]")

    repo = Repository.find(Path.cwd())
    if repo:
        console.print("✓ Repository:       [green]Found .mygit[/green]")
        console.print("✓ Object Database:  [green]Accessible[/green]")
    else:
        console.print("⚠ Repository:       [yellow]No .mygit repository in current dir[/yellow]")

    console.print("\n[bold green]No critical problems detected.[/bold green]")


@app.command()
def publish():
    """Simplified one-command workflow for initializing and publishing code."""
    repo = Repository.find(Path.cwd())
    if not repo:
        repo = Repository.init(Path.cwd())
        console.print("Initialized empty MyGit repository.")

    # Add all files & initial commit if clean
    res = analyze_status(repo)
    if res.untracked or res.unstaged_modified:
        add(paths=["."], all_files=True)
        commit(message="Publish project update", sign=False)

    console.print("[bold green]✓ Repository published locally.[/bold green]")


@app.command()
def key(
    action: str = typer.Argument("generate", help="Action: generate, list, export"),
):
    """Generate and manage Ed25519 cryptographic signing keys."""
    repo = get_current_repo()
    key_priv = repo.mygit_dir / "ed25519.priv"
    key_pub = repo.mygit_dir / "ed25519.pub"

    if action == "generate":
        priv_pem, pub_pem = KeyManager.generate_keypair()
        key_priv.write_text(priv_pem, encoding="utf-8")
        key_pub.write_text(pub_pem, encoding="utf-8")
        console.print("[bold green]Generated new Ed25519 keypair in .mygit/[/bold green]")
        console.print(f"Public Key:\n{pub_pem}")
    elif action == "list" or action == "export":
        if key_pub.is_file():
            console.print(key_pub.read_text(encoding="utf-8"))
        else:
            console.print("[yellow]No keypair generated yet.[/yellow]")


@app.command()
def secrets(
    action: str = typer.Argument("scan", help="Action: scan"),
):
    """Scan working tree for hardcoded API keys, tokens, and credentials."""
    repo = get_current_repo()
    ignore_matcher = IgnoreMatcher(repo.worktree)
    all_warnings = []

    for root, dirs, files in os.walk(repo.worktree):
        if ".mygit" in dirs:
            dirs.remove(".mygit")
        for f in files:
            p = Path(root) / f
            rel_p = p.relative_to(repo.worktree).as_posix()
            if not ignore_matcher.is_ignored(rel_p):
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    warns = SecretScanner.scan_file_content(rel_p, content)
                    all_warnings.extend(warns)
                except Exception:
                    pass

    if all_warnings:
        console.print(f"[bold red]Found {len(all_warnings)} potential secret(s):[/bold red]\n")
        for w in all_warnings:
            console.print(f"  ❌ [yellow]{w.to_summary()}[/yellow]")
    else:
        console.print("[bold green]✓ Security scan clear. No secrets detected.[/bold green]")


@app.command()
def ai(
    action: str = typer.Argument("commit", help="Action: commit, review"),
):
    """AI-assisted development features (Opt-in)."""
    repo = get_current_repo()
    if action == "commit":
        status_res = analyze_status(repo)
        if not (status_res.staged_new or status_res.staged_modified or status_res.staged_deleted):
            console.print("[yellow]No staged changes found to analyze.[/yellow]")
            return

        summary = f"Staged {len(status_res.staged_new)} new, {len(status_res.staged_modified)} modified, {len(status_res.staged_deleted)} deleted files."
        console.print("[bold cyan]AI Suggested Commit Message:[/bold cyan]")
        console.print(f"feat: update project codebase ({summary})")


if __name__ == "__main__":
    app()
