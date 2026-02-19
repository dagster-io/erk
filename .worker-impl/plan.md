# Migrate Objective Linkage: Update Roadmap Step References from Issue Numbers to PR Numbers

Part of Objective #7419, Node 2.5

## Context

Erk is migrating its plan storage from GitHub issues to draft PRs. In the old system, the `plan` field on a roadmap node stored a plan issue number (`plan: "#7423"`). In the new draft-PR system, the plan IS a draft PR, so the `plan` field should store the draft PR number (`plan: "#123"`).

The roadmap YAML format itself is backend-agnostic — it just stores `"#NNN"` strings. The challenge is in the **workflows that populate and read these references**, which currently assume issue-number semantics (extracting plan IDs from `P<number>-` branch name prefixes).

### What Needs to Change

Several sites read or write the `plan` field on objective roadmap nodes. These need to work correctly when the plan reference is a PR number rather than an issue number:

1. **`objective-fetch-context`** — Uses `_parse_plan_number_from_branch()` which only handles `P<number>-` branches. Fails for draft-PR branches (`plan-...`).
2. **`one-shot.yml` workflow** — After plan is saved, calls `update-objective-node --plan "$PLAN_NUMBER"` where `$PLAN_NUMBER` is the plan issue number. With draft-PR backend, the "plan issue" is really a draft PR.
3. **`plan-save.md` Step 3.5** — Calls `update-objective-node --plan "#<issue_number>"`. The `issue_number` comes from `plan-save` output, which already returns the correct plan_id regardless of backend.
4. **`plan_cmd.py` `_update_objective_node()`** — Sets `new_pr=f"#{pr_number}"` with `explicit_status="planning"` when dispatching one-shot. Uses the implementation PR number (correct as-is).

### What Does NOT Need to Change

- **`RoadmapNode` data model** — Already stores `plan: str | None`. The format `"#NNN"` works for both issue and PR numbers.
- **`update_node_in_frontmatter()`** — Three-state semantics (None/empty/value) are backend-agnostic.
- **`update-objective-node` CLI** — Accepts any string for `--plan` and `--pr`. No validation of whether the number is an issue or PR.
- **`_replace_table_in_text()`** — Pure regex replacement, backend-agnostic.
- **`_replace_node_refs_in_body()`** — Delegates to `update_node_in_frontmatter()`, backend-agnostic.
- **`plan-save.md` Step 3.5 call site** — Already uses `issue_number` from the plan-save output, which is the plan_id regardless of backend (issue number or PR number).
- **`objective-update-with-landed-pr`** — Reads `matched_steps` from `objective-fetch-context` output. The matching logic needs fixing (see below), but the update commands themselves are fine.
- **TUI rendering** — Displays `plan` field values as-is. No issue/PR URL resolution needed.
- **Status inference in `update_node_in_frontmatter()`** — Infers `in_progress` when plan is set, regardless of whether it's an issue or PR number.

## Changes

### 1. Fix `objective-fetch-context` plan number extraction

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

The `_parse_plan_number_from_branch()` function only handles `P<number>-` branch prefixes. For draft-PR plans, branches use `plan-...` prefix with no extractable number.

**Change:** Update the plan number discovery to also support resolving the plan ID via the plan backend when branch name extraction fails. This means:

1. Keep `_parse_plan_number_from_branch()` as the fast path for issue-based plans
2. Add a fallback path: when branch name extraction returns `None`, use the plan backend's `resolve_plan_id_for_branch()` to look up the plan ID from the branch name via API
3. This requires adding access to the `plan_backend` from the Click context, which is available via `require_context(ctx).plan_backend`

**Specific changes to `objective_fetch_context()`:**

```python
# Current (line 157):
plan_number = _parse_plan_number_from_branch(branch_name)
if plan_number is None:
    click.echo(_error_json(f"Branch '{branch_name}' does not match P<number>-... pattern"))
    raise SystemExit(1)

# New:
plan_number = _parse_plan_number_from_branch(branch_name)
if plan_number is None:
    # Draft-PR branches don't encode plan number in name.
    # Fall back to plan backend resolution.
    plan_backend = require_plan_backend(ctx)
    plan_id = plan_backend.resolve_plan_id_for_branch(repo_root, branch_name)
    if plan_id is None:
        click.echo(_error_json(
            f"Branch '{branch_name}' has no extractable plan number and no PR found"
        ))
        raise SystemExit(1)
    plan_number = int(plan_id)
```

This requires adding `require_plan_backend` to the imports from `erk_shared.context.helpers` (or however the plan_backend is accessed in exec scripts).

**Important:** Check how other exec scripts access the plan backend. Look at `plan_save.py` and `impl_init.py` for patterns. The plan backend is typically available via `require_context(ctx).plan_backend` or a similar helper.

### 2. Update `_build_roadmap_context()` plan matching

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

The `_build_roadmap_context()` function matches steps using `step.plan == f"#{plan_number}"`. This works for both issue-based and draft-PR plans because both store `"#NNN"` format. **No change needed here** — the format is already backend-agnostic. The fix in step 1 ensures `plan_number` is correctly resolved regardless of backend.

### 3. Update `one-shot.yml` workflow plan reference

**File:** `.github/workflows/one-shot.yml`

Lines 187-202: After plan is created, the workflow calls:
```bash
erk exec update-objective-node "$OBJECTIVE_ISSUE" --node "$NODE_ID" --plan "$PLAN_NUMBER"
```

Where `$PLAN_NUMBER` comes from `steps.read_result.outputs.issue_number` (the plan issue number from plan-result.json).

**Analysis:** This already works correctly because:
- When `PLAN_BACKEND="github"`: `issue_number` in plan-result.json is the plan issue number
- When `PLAN_BACKEND="draft_pr"`: `issue_number` in plan-result.json is the draft PR number (the plan-save command returns plan_id as issue_number in its output contract)
- The `--plan` flag accepts any `"#NNN"` string

**Verify:** Check the plan-save exec script to confirm it outputs the plan_id consistently regardless of backend. The `plan_save.py` dispatcher should return the same JSON shape.

**Change needed:** The `$PLAN_NUMBER` value needs to include the `#` prefix. Currently line 202 passes `--plan "$PLAN_NUMBER"` where `PLAN_NUMBER` is just a number string. Looking at the plan-save command:

```bash
erk exec update-objective-node "$OBJECTIVE_ISSUE" --node "$NODE_ID" --plan "$PLAN_NUMBER"
```

Let me check: `PLAN_NUMBER` is `${{ steps.read_result.outputs.issue_number }}` which is just a number. But the `--plan` flag expects values like `"#6464"`. **This looks like it may already have the `#` prefix or the CLI handles it.** Need to verify the exact value passed.

Actually, looking more carefully at the one-shot.yml line 197:
```yaml
PLAN_NUMBER: ${{ steps.read_result.outputs.issue_number }}
```
And line 202:
```bash
--plan "$PLAN_NUMBER"
```

If `issue_number` is `7570`, then `--plan "7570"` is passed. But the convention is `--plan "#7570"`. Let me verify the actual value format...

Looking at the one-shot-plan command (this file), plan-result.json has `{"issue_number": <num>}` where `<num>` is an integer, so `PLAN_NUMBER` would be the raw number. The `--plan` flag in update-objective-node accepts raw strings that get stored directly. If `"7570"` is stored (without `#`), this would be inconsistent with all other plan references that use `"#7570"`.

**Wait — re-examining the workflow:** The shell variable expansion `"$PLAN_NUMBER"` where PLAN_NUMBER=7570 would pass `--plan "7570"`. But the convention documented everywhere is `--plan "#6464"`. This is a pre-existing bug OR the `#` is added elsewhere.

**After careful review:** This issue already exists in the current code and is out of scope for this plan. The `#` prefix handling for the one-shot workflow plan reference should be verified and fixed if needed, but it's not a draft-PR migration issue — it affects issue-based plans too. **No change for this plan.**

### 4. Update objective auto-discovery in `objective-fetch-context`

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

Lines 162-186: When `objective_number` is not provided, the script discovers it from the plan issue metadata:

```python
plan_for_discovery = issues.get_issue(repo_root, plan_number)
discovered_objective = extract_metadata_value(
    plan_for_discovery.body, "plan-header", "objective_issue"
)
```

This uses `issues.get_issue()` to fetch the plan entity. For issue-based plans, this fetches the issue. For draft-PR plans, the plan entity is a PR, not an issue. `issues.get_issue()` won't find a PR.

**Change:** Use the plan backend to fetch the plan entity instead of directly using issues gateway:

```python
if objective_number is None:
    plan_backend = require_plan_backend(ctx)
    plan_result = plan_backend.get_plan(repo_root, str(plan_number))
    if isinstance(plan_result, PlanNotFound):
        msg = f"Plan #{plan_number} not found (needed to discover objective)"
        click.echo(_error_json(msg))
        raise SystemExit(1)
    if plan_result.objective_id is not None:
        objective_number = plan_result.objective_id
    else:
        msg = f"Plan #{plan_number} has no linked objective"
        click.echo(_error_json(msg))
        raise SystemExit(1)
```

This uses `PlanBackend.get_plan()` which works for both issue-based and draft-PR plans, and the `objective_id` field is populated by both backends from the `plan-header` metadata.

**Required imports:** Add `PlanNotFound` from `erk_shared.plan_store.types` and the plan backend helper.

### 5. Handle `--pr` auto-discovery for draft-PR branches

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

Lines 189-194: When `pr_number` is not provided, the script discovers it:

```python
pr_result = github.get_pr_for_branch(repo_root, branch_name)
```

For issue-based plans, the PR is the implementation PR (separate from the plan issue). For draft-PR plans, there's a subtlety: the draft PR IS the plan, and the same PR becomes the implementation PR after commits are pushed. So `get_pr_for_branch()` would return the plan/implementation PR, which is correct.

**No change needed.** The auto-discovery works correctly for both backends because the implementation PR is always associated with the branch.

### 6. Add plan backend helper to exec script context

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

The exec script currently uses `require_issues()`, `require_github()`, etc. to get gateways from the Click context. We need to add access to the plan backend.

**Check existing patterns:** Look at how `plan_save.py` or other exec scripts access the plan backend. Most likely via `require_context(ctx)` which returns the full `ErkContext` containing `plan_backend`, or there's a dedicated `require_plan_backend(ctx)` helper.

**Specific change:** Add the plan backend accessor to the function's gateway resolution section (around lines 143-145):

```python
issues = require_issues(ctx)
github = require_github(ctx)
repo_root = require_repo_root(ctx)
plan_backend = require_plan_backend(ctx)  # NEW
```

### 7. Update tests for `objective_fetch_context`

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py` (if it exists)

Add test cases for:
- Draft-PR branch name (`plan-...`) where plan number is resolved via plan backend
- Objective auto-discovery via plan backend instead of issues gateway
- Verify the existing issue-based tests still pass (P<number>- branches)

### 8. Verify `plan-save` output contract

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

Verify that the `plan-save` exec command returns consistent JSON output regardless of backend:
- `issue_number`: Should be the plan_id (issue number for issue backend, PR number for draft-PR backend)
- This is used by `plan-save.md` Step 3.5 to call `update-objective-node --plan "#<issue_number>"`

**Expected:** Already correct, since `plan_save.py` dispatches to backend-specific handlers that return the plan_id as `issue_number`. Just verify this assumption.

## Files Changing

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_fetch_context.py` | Add plan backend fallback for plan number resolution; use plan backend for objective discovery |
| `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py` | Add draft-PR branch test cases |

## Files NOT Changing

- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` — Data model is backend-agnostic
- `src/erk/cli/commands/exec/scripts/update_objective_node.py` — CLI accepts any string values
- `.claude/commands/erk/plan-save.md` — Already uses backend-agnostic plan_id
- `.claude/commands/erk/objective-plan.md` — Marker-based flow works with any plan_id
- `.claude/commands/erk/objective-update-with-landed-pr.md` — Consumes fetch-context output, no direct plan ID parsing
- `src/erk/cli/commands/objective/plan_cmd.py` — `_update_objective_node()` uses PR number (correct)
- `.github/workflows/one-shot.yml` — Plan number value comes from plan-result.json which is backend-agnostic
- `src/erk/cli/commands/objective_helpers.py` — `get_objective_for_branch()` uses plan backend
- TUI code — Displays values as-is, no URL resolution needed

## Implementation Details

### Pattern to Follow

The key pattern is **LBYL with plan backend resolution**: try the fast path (branch name extraction) first, then fall back to the plan backend's API-based resolution.

Look at `validate_plan_linkage()` in `packages/erk-shared/src/erk_shared/impl_folder.py` for the canonical example of this two-tier resolution pattern.

### Context Access Pattern

Exec scripts access gateways via Click context helpers. Check `erk_shared/context/helpers.py` for available helpers. The plan backend may be accessible via:
- `require_context(ctx).plan_backend` — if `require_context` returns an ErkContext
- A dedicated `require_plan_backend(ctx)` helper

Look at `plan_save.py`, `impl_init.py`, or `impl_signal.py` for how they access the plan backend in exec scripts.

### Edge Case: Branch Has No Associated PR

For draft-PR branches, `resolve_plan_id_for_branch()` calls `get_pr_for_branch()`. If the branch doesn't have a PR yet (e.g., during initial dispatch before PR creation), this will fail. However, `objective-fetch-context` is only called AFTER the PR exists (during the update-with-landed-pr flow), so this shouldn't happen in practice.

### Edge Case: Mixed Backend References in Same Objective

An objective could have some nodes planned via issue backend and others via draft-PR backend (during the migration period). The `plan` field stores `"#NNN"` regardless, so the roadmap YAML is consistent. The only asymmetry is in **reading the plan reference** — to look up the plan entity (for the `objective-fetch-context` flow), you'd need to know whether `"#123"` is an issue or a PR. The plan backend handles this transparently via `get_plan()`.

## Verification

1. **Unit tests pass** for objective_fetch_context with both branch naming patterns
2. **Existing tests pass** — no regressions in update-objective-node or roadmap parsing tests
3. **Manual verification** (for implementer): Run `erk exec objective-fetch-context` on a draft-PR plan branch and verify it correctly resolves the plan number and matches roadmap steps
4. **Run `ruff` and `ty`** to verify type correctness
5. **Run pytest** for the modified test files