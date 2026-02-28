# Fix: Suppress stale stack (🥞) indicator when parent PR is already merged

## Context

When a stacked PR's parent is merged, Graphite locally re-parents the branch to `master`, but the GitHub PR's `baseRefName` still points to the old (now-deleted) parent branch. The current stack detection logic checks GitHub's `base_ref_name` first and shows 🥞 whenever it's not master/main — even when the stack relationship is stale and the parent has already landed.

**Root cause:** The detection order prioritizes GitHub's `base_ref_name` (line 682-683) over Graphite's local parent tracking (lines 687-692). Graphite is the authoritative source for current stacking state, but it's only consulted as a fallback when GitHub says "not stacked."

**Fix:** Reverse the priority — check Graphite first (authoritative), then fall back to GitHub's `base_ref_name` only when Graphite doesn't track the branch.

## Change

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (lines 682-692)

**Current logic:**
```python
# 1. Check GitHub base_ref_name (primary)
if selected_pr.base_ref_name is not None:
    pr_is_stacked = selected_pr.base_ref_name not in ("master", "main")

# 2. Supplement with Graphite (fallback — only if GitHub said "not stacked")
if pr_is_stacked is not True and pr_head_branch is not None:
    parent = self._ctx.branch_manager.get_parent_branch(...)
    if parent is not None and parent not in ("master", "main"):
        pr_is_stacked = True
```

**New logic:**
```python
# 1. Check Graphite local parent (authoritative when available)
if pr_head_branch is not None:
    parent = self._ctx.branch_manager.get_parent_branch(
        self._location.root, pr_head_branch
    )
    if parent is not None:
        pr_is_stacked = parent not in ("master", "main")

# 2. Fall back to GitHub base_ref_name (when branch not tracked by Graphite)
if pr_is_stacked is None and selected_pr.base_ref_name is not None:
    pr_is_stacked = selected_pr.base_ref_name not in ("master", "main")
```

Key differences:
- Graphite is checked **first** and its answer is definitive (sets `True` or `False`)
- GitHub `base_ref_name` only consulted when `pr_is_stacked` is still `None` (Graphite had no opinion)
- When parent PR is merged and Graphite says parent=master, `pr_is_stacked = False` — no 🥞

## Verification

1. Run existing lifecycle display tests: `pytest tests/unit/plan_store/test_lifecycle_display.py`
2. Run plan data provider tests: `pytest tests/unit/plan_store/`
3. Verify in `erk dash` that PR #8456 no longer shows 🥞 (since Graphite parent is `master`)
