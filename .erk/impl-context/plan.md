# Plan: Rename `issue_number` → `plan_number` in Phase 8.1

**Part of Objective #7724, Node 8.1**

## Context

Objective #7724 is a multi-phase rename of `issue_number` to `plan_number` across plan-related code. Phases 1-6 are done, 7.1 is in progress (#8349). Node 8.1 targets CLI command files: `launch_cmd.py`, `land_cmd.py`, `one_shot_dispatch.py`, `branch/create_cmd.py`, `branch/checkout_cmd.py`, `implement.py`, and `implement_shared.py`.

## Scope & Boundaries

**In scope:** Rename local variables, function parameters, Click options, docstrings, and user-facing strings in the 7 target files.

**Out of scope (Phase 9):**
- `IssueBranchSetup.issue_number` field in `erk_shared/issue_workflow.py` — keep `.issue_number` field accesses
- `create_submission_queued_block(issue_number=...)` parameter in `erk_shared/gateway/github/metadata/core.py` — keep kwarg name

## Files & Changes

### 1. `src/erk/cli/commands/implement.py` (6 renames)

Rename function parameter and all usage in `_implement_from_issue()`:

| Line | Before | After |
|------|--------|-------|
| 74 | `issue_number: str,` | `plan_number: str,` |
| 88 | docstring `issue_number:` | `plan_number:` |
| 104 | `get_plan(repo.root, issue_number)` | `get_plan(repo.root, plan_number)` |
| 106 | `f"Plan #{issue_number} not found"` | `f"Plan #{plan_number} not found"` |
| 114 | `f"Plan #{issue_number} does not..."` | `f"Plan #{plan_number} does not..."` |
| 122 | `f"Would create impl folder from plan #{issue_number}\n..."` | `...#{plan_number}\n..."` |
| 161 | `plan_id=str(issue_number),` | `plan_id=str(plan_number),` |
| 174 | `f"#{issue_number}"` | `f"#{plan_number}"` |
| 427 | `issue_number=target_info.plan_number,` | `plan_number=target_info.plan_number,` |

### 2. `src/erk/cli/commands/implement_shared.py` (5 renames)

Rename parameter in `prepare_plan_source_from_issue()`:

| Line | Before | After |
|------|--------|-------|
| 499 | `issue_number: str, base_branch: str` | `plan_number: str, base_branch: str` |
| 508 | docstring `issue_number:` | `plan_number:` |
| 521 | `get_plan(repo_root, issue_number)` | `get_plan(repo_root, plan_number)` |
| 523 | `f"Error: Plan #{issue_number} not found"` | `...#{plan_number} not found"` |
| 541 | `f"Would create worktree from plan #{issue_number}\n..."` | `...#{plan_number}\n..."` |

Also update callers that pass `issue_number=` to this function (search for call sites).

### 3. `src/erk/cli/commands/launch_cmd.py` (7 renames)

Rename Click option and all usage:

| Line | Before | After |
|------|--------|-------|
| 243-244 | `"--issue", "issue_number"` | `"--plan", "plan_number"` |
| 246 | `help="Issue number (required for learn)"` | `help="Plan number (required for learn)"` |
| 264 | `issue_number: int \| None,` | `plan_number: int \| None,` |
| 331 | `issue_number is not None,` | `plan_number is not None,` |
| 332 | `"--issue is required for learn workflow"` | `"--plan is required for learn workflow"` |
| 334 | `assert issue_number is not None` | `assert plan_number is not None` |
| 335 | `_trigger_learn(ctx, repo, issue=issue_number)` | `_trigger_learn(ctx, repo, issue=plan_number)` |
| 337 | `issue=issue_number or 0` | `issue=plan_number or 0` |

Also rename in `_trigger_learn()`:

| Line | Before | After |
|------|--------|-------|
| 190 | `f"Triggering learn workflow for issue #{issue}..."` | `f"Triggering learn workflow for plan #{issue}..."` |
| 193 | `"issue_number": str(issue),` | `"plan_number": str(issue),` |

**Note:** The learn.yml workflow expects `plan_id` as input, not `issue_number`. The existing `"issue_number"` key was already mismatched. Rename to `"plan_number"` for consistency with the objective; the workflow input name mismatch is a separate concern (not in scope).

### 4. `src/erk/cli/commands/one_shot_dispatch.py` (local variable rename)

Rename `plan_issue_number` → `plan_number`:

| Line | Before | After |
|------|--------|-------|
| 189 | `plan_issue_number: int \| None = None` | `plan_number: int \| None = None` |
| 308 | `plan_issue_number = pr_number` | `plan_number = pr_number` |
| 327 | `if plan_issue_number is not None:` | `if plan_number is not None:` |
| 328 | `inputs["plan_issue_number"] = str(plan_issue_number)` | `inputs["plan_issue_number"] = str(plan_number)` |
| 352 | `if plan_issue_number is not None:` | `if plan_number is not None:` |
| 359 | `plan_number=plan_issue_number,` | `plan_number=plan_number,` |
| 376 | `issue_number=plan_issue_number,` | `issue_number=plan_number,` |
| 389 | `ctx.issues.add_comment(repo.root, plan_issue_number, ...)` | `..., plan_number, ...)` |

**Keep unchanged:**
- Line 328 dict key `"plan_issue_number"` — this is a workflow input that matches `one-shot.yml`
- Line 376 kwarg `issue_number=` — this calls `create_submission_queued_block()` in erk-shared (Phase 9)

### 5. `src/erk/cli/commands/branch/create_cmd.py` (3 local variable renames)

| Line | Before | After |
|------|--------|-------|
| 136 | `issue_number = parse_issue_identifier(for_plan)` | `plan_number = parse_issue_identifier(for_plan)` |
| 137 | `ctx.plan_store.get_plan(repo.root, str(issue_number))` | `..., str(plan_number))` |
| 139 | `f"Issue #{issue_number} not found"` | `f"Plan #{plan_number} not found"` |

**Keep unchanged:** Lines 256, 269, 275, 280 — `setup.issue_number` accesses (Phase 9, from `IssueBranchSetup`)

### 6. `src/erk/cli/commands/branch/checkout_cmd.py` (3 local variable renames)

| Line | Before | After |
|------|--------|-------|
| 409 | `issue_number = parse_issue_identifier(for_plan)` | `plan_number = parse_issue_identifier(for_plan)` |
| 410 | `ctx.plan_store.get_plan(repo.root, str(issue_number))` | `..., str(plan_number))` |
| 412 | `f"Issue #{issue_number} not found"` | `f"Plan #{plan_number} not found"` |

**Keep unchanged:** Lines 307, 319, 325, 330 — `setup.issue_number` accesses (Phase 9)

### 7. `src/erk/cli/commands/land_cmd.py` — No changes needed

No `issue_number` occurrences found.

## Callers of Renamed Functions

After renaming `_implement_from_issue(issue_number=...)` and `prepare_plan_source_from_issue(issue_number=...)`, search for all callers and update the kwarg name:

- `implement.py` line 427 — already identified above
- Any other callers of `prepare_plan_source_from_issue()` — need to search

## Implementation Order

1. `implement_shared.py` — shared function, rename parameter
2. Update all callers of `prepare_plan_source_from_issue(issue_number=...)` to use `plan_number=`
3. `implement.py` — rename `_implement_from_issue` parameter and its call site
4. `launch_cmd.py` — rename Click option and variable
5. `one_shot_dispatch.py` — rename local variable
6. `branch/create_cmd.py` — rename local variable
7. `branch/checkout_cmd.py` — rename local variable

## Verification

1. `ruff check src/erk/cli/commands/implement.py src/erk/cli/commands/implement_shared.py src/erk/cli/commands/launch_cmd.py src/erk/cli/commands/one_shot_dispatch.py src/erk/cli/commands/branch/create_cmd.py src/erk/cli/commands/branch/checkout_cmd.py`
2. `ty check` on the modified files
3. Run existing tests for these files (search for test files matching each module name)
4. Grep for remaining `issue_number` in modified files to confirm none were missed (excluding `setup.issue_number` and cross-boundary kwargs)
