# Fix Merge Conflicts for Rebase

## Context

Rebasing branch `plnd/fix-learned-docs-drift-02-28-0930` onto `b774fde49`. Two files have conflicts.

## Conflicts

### 1. `docs/learned/tripwires-index.md` (AUTO-GENERATED)

Has `<!-- AUTO-GENERATED FILE -->` header. Conflict is just a tripwires count difference (124 vs 118). Accept `--theirs`, stage it, and regenerate with `erk docs sync` after rebase completes.

### 2. `docs/learned/planning/impl-context.md` (real content)

Lines 68-72. Both sides modify the same sentence about the LBYL guard:
- **HEAD**: `...Both submit paths use this pattern...behind (fixed in PR #7687).`
- **Incoming**: `...Both submit paths (submit pipeline and dispatch) use this pattern...behind.`

These are complementary. Merge both: keep "(submit pipeline and dispatch)" from incoming AND "(fixed in PR #7687)" from HEAD.

Resolved line:
```
See the `impl_context_exists()` / `remove_impl_context()` LBYL guard in `packages/erk-shared/src/erk_shared/impl_context.py`. Both submit paths (submit pipeline and dispatch) use this pattern to prevent errors from a prior failed submission leaving a stale `.erk/impl-context/` directory behind (fixed in PR #7687).
```

## Steps

1. Resolve `tripwires-index.md`: `git checkout --theirs docs/learned/tripwires-index.md && git add docs/learned/tripwires-index.md`
2. Edit `impl-context.md`: Replace the conflict block (lines 68-72) with the merged sentence, then `git add`
3. `git rebase --continue`
4. If more conflicts appear, repeat
5. Run `erk docs sync` to regenerate auto-generated files
6. Commit regenerated files separately

## Verification

- `git status` shows clean working tree after rebase
- `git log` shows the rebased commit
- No conflict markers remain in any files
