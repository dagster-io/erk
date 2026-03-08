# Phase 2: Idempotent Reconcile (Objective #8950, Nodes 2.1–2.3)

**Part of Objective #8950, Nodes 2.1, 2.2, 2.3**

## Context

`erk reconcile` processes merged PRs through a post-merge lifecycle (learn plan creation, objective node updates, label stamping). If run twice on the same PRs — or if `erk land` already ran part of the lifecycle — steps can duplicate: duplicate learn plan PRs, duplicate objective action comments, and `erk-reconciled` label stamped on non-erk PRs.

Phase 2 adds idempotency guards so `erk reconcile` is always safe to re-run.

## Acceptance Test

Running `erk reconcile` twice in a row produces identical results with no duplicate learn PRs, no duplicate objective action comments, and `erk-reconciled` only stamped on PRs with the `erk-pr` label.

---

## Node 2.1 — Guard learn plan creation

**File:** `src/erk/cli/commands/land_learn.py`

### Problem

`_create_learn_pr_for_merged_branch` (and the land path `_create_learn_pr_impl`) only check for cycle prevention (`erk-learn` label) before creating a learn plan. Running twice creates duplicate learn plan PRs.

### Fix

**Check before:** After fetching `plan_result`, check `plan_result.header_fields.get("learn_plan_issue")`.
If set, a learn plan already exists — log and return early.

```python
existing_learn = plan_result.header_fields.get("learn_plan_issue")
if existing_learn is not None:
    user_output(
        click.style("ℹ", fg="blue")
        + f" Learn plan already exists (#{existing_learn}) for plan #{plan_id}, skipping"
    )
    return
```

**Set after:** After successful `create_plan_draft_pr` call (when `result.success`), write the backpointer on the source plan:

```python
ctx.plan_backend.update_metadata(
    main_repo_root,
    plan_id,
    {"learn_plan_issue": int(result.plan_number), "learn_status": "completed_with_plan"},
)
```

This uses the existing `PlanBackend.update_metadata` method (same as `track-learn-result` exec script).

**Apply to both functions:**
- `_create_learn_pr_for_merged_branch` (reconcile path, lines 105–225)
- `_create_learn_pr_impl` (land path, lines 527–634)

**Tests:** New test file `tests/unit/cli/commands/test_land_learn.py`
- Test that second call with `learn_plan_issue` already set → returns early with log message, no new PR created
- Test that successful first call sets `learn_plan_issue` on the source plan

---

## Node 2.2 — Guard objective updates

**File:** `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

### Problem

`objective-apply-landed-update` always posts an action comment, even when no nodes changed (nodes already "done" with the matching PR). Running twice creates duplicate action comments on the objective issue.

### Fix 1 — Exclude already-done nodes from matched_steps

In the auto-match block (lines 241–246), filter out nodes already marked "done" with this PR:

```python
matched_steps = [
    node["id"]
    for phase in roadmap["phases"]
    for node in phase["nodes"]
    if node["pr"] == pr_ref and node["status"] != "done"
]
```

When `--node` flags are provided explicitly, filter those too — skip any node whose current status is already "done" with `pr_ref`.

### Fix 2 — Skip action comment if nothing changed

After `_update_nodes_in_body`, only post the action comment if `node_updates` is non-empty:

```python
action_comment_id: int | None = None
if node_updates:
    comment_body = _format_action_comment(...)
    action_comment_id = issues.add_comment(repo_root, objective_number, comment_body)
```

Update the result dict so `action_comment_id` can be `None` (already typed as `int | None` in `ApplyLandedUpdateResultDict`).

**Tests:** Add to `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
- Test: node already "done" with same PR → not included in `matched_steps`, not in `node_updates`, no action comment posted
- Test: node "done" with a DIFFERENT PR → still skipped (pr_ref check fails anyway since it won't match)
- Test: mix of done and pending nodes → only pending nodes updated, comment posted for pending only

---

## Node 2.3 — Guard label stamping scope

**File:** `src/erk/cli/commands/reconcile_pipeline.py`

### Problem

`process_merged_branch` stamps `erk-reconciled` on ALL processed PRs, including non-erk PRs found by local gone-branch detection. The objective design says: "No `erk-reconciled` label stamped on non-erk PRs."

### Fix

Before the label stamping block (currently line 259), add a guard:

```python
# 3. Stamp reconciled label only on erk-pr PRs (fail-open)
if ctx.github.has_pr_label(main_repo_root, info.pr_number, ERK_PR_LABEL):
    try:
        ctx.github.add_label_to_pr(main_repo_root, info.pr_number, ERK_RECONCILED_LABEL)
    except Exception as exc:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to add reconciled label to PR #{info.pr_number}: {exc}"
        )
```

`has_pr_label` is idempotent (read-only) and already exists on the `GitHub` gateway ABC with fake and real implementations.

**Tests:** New test file `tests/unit/cli/commands/test_reconcile_pipeline.py`
- Test: non-erk PR (no `erk-pr` label) → `erk-reconciled` NOT stamped, other lifecycle steps still run
- Test: erk PR (has `erk-pr` label) → `erk-reconciled` IS stamped
- Use `FakeLocalGitHub` with `_pr_labels` configured to control `has_pr_label` return

---

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/land_learn.py` | Add idempotency guard + backpointer set in `_create_learn_pr_for_merged_branch` and `_create_learn_pr_impl` |
| `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py` | Filter already-done nodes; skip action comment when no updates |
| `src/erk/cli/commands/reconcile_pipeline.py` | Guard `add_label_to_pr` with `has_pr_label(ERK_PR_LABEL)` check |

## Files to Create

| File | Content |
|------|---------|
| `tests/unit/cli/commands/test_land_learn.py` | Tests for idempotent learn plan creation |
| `tests/unit/cli/commands/test_reconcile_pipeline.py` | Tests for label scoping |

## Key Reused APIs

- `PlanBackend.update_metadata(repo_root, plan_id, metadata)` — already in `planned_pr.py:448`
- `GitHub.has_pr_label(repo_root, pr_number, label)` — already in `abc.py:561`, `fake.py:871`
- `FakeLocalGitHub` with `_pr_labels` — supports `has_pr_label` assertions
- `context_for_test(...)` from `erk_shared.context.testing` — for CLI tests
