# MyGit Merge & Diff Engine Theory

## 1. Graph Theory & Lowest Common Ancestor (LCA)

Merging two diverging branches $A$ (Ours) and $B$ (Theirs) requires finding their **Lowest Common Ancestor (LCA)** commit, denoted as $L = \text{LCA}(A, B)$.

```text
         (L) Merge Base
          Commit 10
          /      \
         /        \
        ▼          ▼
    Commit 11   Commit 12
    (Ours / A)  (Theirs / B)
         \        /
          ▼      ▼
         Commit 13
       (Merge Commit)
```

### LCA Algorithm in MyGit:
1. Traverse backward from $A$ via Breadth-First Search (BFS) to collect all reachable ancestor commit SHAs into set $S_A$.
2. Traverse backward from $B$ via BFS. The first commit SHA encountered that belongs to $S_A$ is the Lowest Common Ancestor $L$.

---

## 2. Merge Strategies

### 2.1 Fast-Forward Merge Strategy
If $L = A$ (i.e. Our current branch commit $A$ is an exact ancestor of Theirs $B$), no merge commit is required:
- Update branch reference pointer directly to $B$.
- Restore working tree to match tree of $B$.

---

### 2.2 3-Way Merge Strategy
When $A$ and $B$ have diverged from base $L$, MyGit evaluates changes per file using 3 snapshot inputs:
- $L(\text{path})$: Content at Merge Base $L$.
- $A(\text{path})$: Content at Our branch commit $A$.
- $B(\text{path})$: Content at Their branch commit $B$.

#### Decision Matrix:

| $L(\text{path})$ vs $A(\text{path})$ | $L(\text{path})$ vs $B(\text{path})$ | Resulting Action |
|---|---|---|
| Unchanged ($A = L$) | Modified ($B \neq L$) | Take $B(\text{path})$ automatically (Clean) |
| Modified ($A \neq L$) | Unchanged ($B = L$) | Keep $A(\text{path})$ automatically (Clean) |
| Identical change ($A = B$) | Identical change ($B = A$) | Keep $A(\text{path})$ (Clean) |
| Modified ($A \neq L$) | Modified differently ($B \neq L$, $A \neq B$) | **Conflict! Generate conflict markers** |

---

## 3. Conflict Marker Format

When a line-level conflict is detected:

```text
<<<<<<< OURS
Current branch code line
=======
Incoming branch code line
>>>>>>> THEIRS
```

MyGit writes conflict state metadata into `.mygit/MERGE_HEAD` and `.mygit/MERGE_MSG` until resolved by `mygit merge --continue` or reset via `mygit merge --abort`.
