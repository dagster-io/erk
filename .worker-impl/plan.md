<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary>plan-header</summary>

```yaml

schema_version: '2'
created_at: '2026-02-20T13:00:43.834597+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22236894225'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFLWwUEQ
last_dispatched_at: '2026-02-20T18:51:11.707402+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-fix-learn-pipeline-for-dra-02-20-1300
created_from_session: 6e7f3404-2ce4-4fd2-9208-973a048c86e3
lifecycle_stage: planned

```

</details>
<!-- /erk:metadata-block:plan-header -->


---

<details>
<summary>original-plan</summary>

# Fix Learn Pipeline for Draft-PR Plans

## Context

The learn pipeline (triggered during `erk land`) was built for the GitHub issue backend. With the draft-PR backend (where the plan IS the PR), several steps fail. Observed with plan #7618:

1. **"No PR found"** — PR discovery can't find the PR via branch-name metadata
2. **"plan-header block not found in PR body"** — Gist URL storage fails

Holistic analysis of the full learn pipeline identified 6 fixes across 3 tiers.

## Holistic Analysis Summary

The learn pipeline has two flows:
- **Local async flow** (`erk land` → `trigger_async_learn.py`): Preprocesses sessions, uploads gist, triggers CI
- **CI flow** (`learn.yml` → `/erk:learn` skill): Runs analysis agents, creates learn plan issue

| Component | Uses plan_backend? | Draft-PR status |
|---|---|---|
| `_check_learn_status_and_prompt()` | Yes | ✅ Works |
| `_discover_sessions()` / `get-learn-sessions` | Yes | ✅ Works |
| `_get_pr_for_plan_direct()` | Partially | ❌ Broken |
| `_store_learn_materials_gist_url()` | Yes | ❌ Missing error handling |
| `get-pr-for-plan` exec script | No (direct `github_issues`) | ❌ Broken |
| `track-learn-result` exec script | Yes | ⚠️ Generic error message |
| `track-learn-evaluation` exec script | Yes | ⚠️ Generic error message |
| `get-issue-body` exec script | `github_issues` | ✅ Works (PRs are issues) |
| Discussion comments fetch | `github_issues` | ✅ Works (PRs are issues) |
| `/erk:learn` skill | N/A (text) | ⚠️ "Issue" terminology |
| `close_review_pr()` | Yes | ✅ Already skips for draft-PR |
| `update_learn_plan()` | Yes | ✅ Already catches PlanHeaderNotFoundError |

---

## Tier 1: Blocking Fixes (3 fixes)

### Fix 1: `_get_pr_for_plan_direct()` — Add draft-PR shortcut

**File:** `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:271`

**Problem:** Tries branch-name metadata → `P{id}-` fallback → fails. For draft-PR, `plan_id` IS the PR number.

**Fix:** Add early return at top of function:

```python
# Draft-PR: plan_id IS the PR number — look up directly
if plan_backend.get_provider_name() == "github-draft-pr":
    pr_result = github.get_pr(repo_root, int(plan_id))
    if isinstance(pr_result, PRNotFound):
        return None
    return {
        "success": True,
        "pr_number": pr_result.number,
        "pr": {
            "number": pr_result.number,
            "title": pr_result.title,
            "state": pr_result.state,
            "url": pr_result.url,
            "head_ref_name": pr_result.head_ref_name,
            "base_ref_name": pr_result.base_ref_name,
        },
    }
```

No new imports needed — `PRNotFound` already imported.

### Fix 2: `_store_learn_materials_gist_url()` — Comment fallback

**File:** `src/erk/cli/commands/land_cmd.py:558`

**Problem:** `update_metadata()` raises `PlanHeaderNotFoundError` when metadata block is missing. Currently caught as generic `RuntimeError`, gist URL discarded.

**Fix:** Catch `PlanHeaderNotFoundError` specifically, fall back to `add_comment()`:

```python
try:
    ctx.plan_backend.update_metadata(repo_root, plan_id, {"learn_materials_gist_url": gist_url})
except PlanHeaderNotFoundError:
    # No metadata block — store as comment instead
    try:
        ctx.plan_backend.add_comment(repo_root, plan_id, f"Learn materials gist: {gist_url}")
    except RuntimeError as comment_err:
        user_output(click.style("⚠ ", fg="yellow") + f"Could not store gist URL on plan {plan_id}: {comment_err}")
except RuntimeError as e:
    user_output(click.style("⚠ ", fg="yellow") + f"Could not store gist URL on plan {plan_id}: {e}")
```

**Import to add:** `from erk_shared.plan_store.types import PlanHeaderNotFoundError`

### Fix 3: `get_pr_for_plan.py` exec script — Use plan_backend

**File:** `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py:57-123`

**Problem:** Uses `github_issues.get_issue()` directly and branch-name resolution. For draft-PR plans, the plan_id IS the PR number — the entire branch-name dance is unnecessary.

**Fix:** Import `require_plan_backend` and add draft-PR shortcut at top of command:

```python
from erk_shared.context.helpers import require_plan_backend

# At top of get_pr_for_plan function body:
plan_backend = require_plan_backend(ctx)

# Draft-PR: plan_id IS the PR number — look up directly
if plan_backend.get_provider_name() == "github-draft-pr":
    pr_result = github.get_pr(repo_root, issue_number)
    if isinstance(pr_result, PRNotFound):
        return _exit_with_error(error="no-pr-for-branch", message=f"PR #{issue_number} not found")
    pr_data = {
        "number": pr_result.number,
        "title": pr_result.title,
        "state": pr_result.state,
        "url": pr_result.url,
        "head_ref_name": pr_result.head_ref_name,
        "base_ref_name": pr_result.base_ref_name,
    }
    success_result = GetPrForPlanSuccess(success=True, pr=pr_data)
    click.echo(json.dumps(asdict(success_result)))
    return

# ... existing issue-based path continues below unchanged
```

---

## Tier 2: Error Handling Improvements (2 fixes)

### Fix 4: `track-learn-result.py` — Specific PlanHeaderNotFoundError handling

**File:** `src/erk/cli/commands/exec/scripts/track_learn_result.py:157-174`

**Current:** Catches `RuntimeError` with generic message "Failed to update learn status".

**Fix:** Add `PlanHeaderNotFoundError` catch before `RuntimeError`:

```python
from erk_shared.plan_store.types import PlanHeaderNotFoundError

try:
    backend.update_metadata(...)
except PlanHeaderNotFoundError:
    error = TrackLearnResultError(
        success=False,
        error="no-metadata-block",
        message=f"Plan {plan_id} has no plan-header metadata block — cannot update learn status",
    )
    click.echo(json.dumps(asdict(error)), err=True)
    raise SystemExit(1) from None
except RuntimeError as e:
    # ... existing handler
```

### Fix 5: `track-learn-evaluation.py` — Specific PlanHeaderNotFoundError handling

**File:** `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py:112-128`

Same pattern as Fix 4. Add `PlanHeaderNotFoundError` catch with specific error type `"no-metadata-block"`.

---

## Tier 3: Skill Documentation (1 fix)

### Fix 6: `/erk:learn` skill — Update terminology

**File:** `.claude/commands/erk/learn.md`

Replace "issue" with "plan" in user-facing text where the reference is to the plan entity (not specifically a GitHub issue). Key changes:

- Line 3: `argument-hint: "[plan-number]"` (was `"[issue-number]"`)
- Line 13: `# Infers plan from current branch` (was `# Infers issue`)
- Line 14: `# Explicit plan number` (was `# Explicit issue number`)
- Lines 31, 41: `plan #<plan-number>` (was `plan #<issue-number>`)
- Lines 52-53: `erk exec get-issue-body <plan-number>` (keep command name, change parameter description)
- Line 113: `erk exec get-learn-sessions <plan-number>` (was `<issue-number>`)
- Line 148: `erk exec get-pr-for-plan <plan-number>` (was `<issue-number>`)

Keep command names unchanged (they still work) — just update the variable names and descriptions to say "plan" instead of "issue".

---

## Tests

### Fix 1 Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`

Reuse: `_make_pr_details`, `_parse_json_output`, `_get_stderr_lines`

1. **`test_get_pr_for_plan_direct_draft_pr_backend`** — Create `DraftPRPlanBackend` with `FakeGitHub` that has a PR. Call `_get_pr_for_plan_direct()`. Assert returns PR details directly.
2. **`test_get_pr_for_plan_direct_draft_pr_backend_not_found`** — PR doesn't exist. Assert returns `None`.

Import: `DraftPRPlanBackend` from `erk_shared.plan_store.draft_pr`, `FakeTime` from `erk_shared.gateway.time.fake`

### Fix 2 Tests

**File:** `tests/unit/cli/commands/land/test_learn_status.py`

1. **`test_store_learn_materials_gist_url_comment_fallback_on_missing_metadata`** — Create `DraftPRPlanBackend` with `FakeGitHub` that has a PR with no metadata block. Call `_store_learn_materials_gist_url()`. Assert `FakeGitHub.pr_comments` contains the gist URL.

Use `context_for_test(plan_store=draft_backend, github=fake_gh, ...)` from `erk.core.context`.

### Fix 3 Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py` (may need to create)

1. **`test_get_pr_for_plan_draft_pr_backend`** — With `DraftPRPlanBackend`, call the command. Assert returns PR details directly without needing metadata block.
2. **`test_get_pr_for_plan_draft_pr_backend_not_found`** — PR doesn't exist. Assert error output.

---

## Key Files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — Fix 1
- `src/erk/cli/commands/land_cmd.py` — Fix 2
- `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` — Fix 3
- `src/erk/cli/commands/exec/scripts/track_learn_result.py` — Fix 4
- `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py` — Fix 5
- `.claude/commands/erk/learn.md` — Fix 6
- `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` — Reference
- `packages/erk-shared/src/erk_shared/plan_store/types.py:79` — PlanHeaderNotFoundError
- `erk.core.context:context_for_test` — Test helper (accepts `plan_store` param)

## Verification

1. Run affected test files:
   - `uv run pytest tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py -v`
   - `uv run pytest tests/unit/cli/commands/land/test_learn_status.py -v`
   - `uv run pytest tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py -v`
2. Run fast-ci to verify no regressions


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7670 --script)" && erk pr sync --dangerous
```
