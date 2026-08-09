import difflib
from typing import Dict, List, Tuple

from mygit_core.index import Index
from mygit_core.objects import ObjectStore, Tree


def get_tree_files(object_store: ObjectStore, tree_sha: str, prefix: str = "") -> Dict[str, str]:
    """Recursively parses a Tree object and returns mapping of {rel_path: blob_sha}."""
    result = {}
    if not tree_sha:
        return result

    try:
        type_name, data = object_store.read_object(tree_sha)
        if type_name != "tree":
            return result

        tree = Tree.parse_data(data)
        for entry in tree.entries:
            path = f"{prefix}/{entry.name}" if prefix else entry.name
            if entry.type_name == "blob":
                result[path] = entry.sha
            elif entry.type_name == "tree":
                result.update(get_tree_files(object_store, entry.sha, path))
    except Exception:
        pass

    return result


def compute_unified_diff(
    old_content: str, new_content: str, old_filename: str, new_filename: str
) -> str:
    """Generates unified diff representation between old_content and new_content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{old_filename}",
        tofile=f"b/{new_filename}",
    )
    return "".join(diff)


def compute_diff_stat(
    diff_map: Dict[str, Tuple[str, str]]
) -> Tuple[str, int, int]:
    """
    Computes git diff --stat representation.
    diff_map format: {filename: (old_text, new_text)}
    Returns (stat_text, total_insertions, total_deletions).
    """
    stat_lines = []
    tot_add = 0
    tot_del = 0

    for path, (old_text, new_text) in diff_map.items():
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        adds = 0
        dels = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                dels += i2 - i1
                adds += j2 - j1
            elif tag == "delete":
                dels += i2 - i1
            elif tag == "insert":
                adds += j2 - j1

        tot_add += adds
        tot_del += dels
        changes = adds + dels
        bar = "+" * min(adds, 20) + "-" * min(dels, 20)
        stat_lines.append(f" {path:<30} | {changes:>4} {bar}")

    summary = f" {len(diff_map)} file(s) changed, {tot_add} insertion(s)(+), {tot_del} deletion(s)(-)"
    stat_lines.append(summary)
    return "\n".join(stat_lines), tot_add, tot_del
