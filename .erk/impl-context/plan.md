# Rename issue_number to plan_number in Phase 4.1 exec scripts

## Context

This is **node 4.1** of objective #7724 ("Rename issue_number to plan_number in plan-related code"). Phases 1–3 (PRs #7849, #7896, #7908, #8122) have already renamed identifiers in `implement_shared.py`, `implement.py`, the `plan_*` exec scripts, and the `impl_*`/`check_impl` exec scripts.

Phase 4.1 targets 12 miscellaneous exec scripts (the 13th file `update_dispatch_info.py` does not exist in the codebase). The rename follows the same pattern established in phases 1–3: rename `issue_number` → `plan_number` in variables, parameters, Click arguments/options, dataclass fields, JSON output keys, docstrings, and comments. Rename `issue_url` → `plan_url` where it appears as a JSON output key.

**Scope boundary**: This plan covers ONLY the 12 exec scripts listed below. Upstream shared functions that these scripts call (`build_pr_body_footer` in `packages/erk-shared/`, `assemble_pr_body` in `pr/shared.py`, `write_dispatch_metadata` in `pr/metadata_helpers.py`) are NOT renamed here — they are scheduled for phases 6 and 7. When an in-scope script calls an out-of-scope function with an `issue_number=` keyword argument, keep the keyword argument name matching the callee's current signature.

**Scope boundary for callers**: `.claude/commands/` and `.github/workflows/` that parse JSON output from these scripts need updating where they reference `issue_number`/`issue_url` JSON keys. However, `plan_save_to_issue.py` already outputs `plan_number` (it was renamed in phase 2), so callers for that script are already correct.

## Files Changed

### 1. `src/erk/cli/commands/exec/scripts/get_plan_metadata.py`

**Rename `issue_number` → `plan_number`:**
- Line 30: Dataclass field `issue_number: int` → `plan_number: int` in `MetadataSuccess`
- Line 44: Click argument `@click.argument("issue_number", type=int)` → `@click.argument("plan_number", type=int)`
- Line 49: Function parameter `issue_number: int` → `plan_number: int`
- Line 60: `plan_id = str(issue_number)` → `plan_id = str(plan_number)`
- Line 68: Error message `f"Issue #{issue_number} not found"` → `f"Plan #{plan_number} not found"`
- Line 77: `issue_number=issue_number` → `plan_number=plan_number`

**Docstring updates:**
- Line 4: `erk exec get-plan-metadata <issue-number>` → `erk exec get-plan-metadata <plan-number>`

### 2. `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`

**Rename `issue_number` → `plan_number`:**
- Line 50: Click argument `@click.argument("issue_number", type=int)` → `@click.argument("plan_number", type=int)`
- Line 54: Function parameter `issue_number: int` → `plan_number: int`
- Line 64: `github.get_pr(repo_root, issue_number)` → `github.get_pr(repo_root, plan_number)`
- Line 66: Error message `f"PR #{issue_number} not found"` → `f"PR #{plan_number} not found"`

**Docstring updates:**
- Line 4: `erk exec get-pr-for-plan <issue-number>` → `erk exec get-pr-for-plan <plan-number>`

### 3. `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py`

**Rename `issue_number` → `plan_number`:**
- Line 26: Click option `--issue-number` → `--plan-number`
- Line 35: Function parameter `issue_number: int` → `plan_number: int`
- Line 55: `issue_number=issue_number` — **KEEP AS `issue_number=plan_number`** (callee `write_dispatch_metadata` uses `issue_number` param, out of scope for this phase)
- Line 65: `issues.get_issue(repo_root, issue_number)` → `issues.get_issue(repo_root, plan_number)`
- Line 67: Error message `f"Issue #{issue_number} not found"` → `f"Plan #{plan_number} not found"`
- Line 80: `issue_number,` → `plan_number,` (arg to `add_comment`)
- Line 91: Comment `# Guard: skip when issue_number == pr_number` → `# Guard: skip when plan_number == pr_number`
- Line 93: `if issue_number == pr_number:` → `if plan_number == pr_number:`
- Line 100: `f"Closes {plans_repo}#{issue_number}"` → `f"Closes {plans_repo}#{plan_number}"` and `f"Closes #{issue_number}"` → `f"Closes #{plan_number}"`
- Line 110: `str(issue_number),` → `str(plan_number),`

**Docstring updates:**
- Line 1: Update docstring references to use "plan" terminology
- Line 41: `"""Register a one-shot plan with issue metadata…"""` → `"""Register a one-shot plan with plan metadata…"""`

### 4. `src/erk/cli/commands/exec/scripts/create_plan_from_context.py`

**Rename JSON output keys:**
- Line 103: `"issue_number": result.number,` → `"plan_number": result.number,`
- Line 104: `"issue_url": result.url,` → `"plan_url": result.url,`

**Docstring updates:**
- Line 46: `JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}` → `JSON object: {"success": true, "plan_number": 123, "plan_url": "..."}`
- Line 63: Comment `since we don't have issue number yet` → `since we don't have plan number yet`
- Line 90: Comment `Now that we have the issue number` → `Now that we have the plan number`
- Line 93: Comment `Update the issue body` → `Update the plan issue body`

### 5. `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py`

**Rename `issue_number` → `plan_number`:**
- Line 48: Click option `--issue`, dest stays `"issue_number"` → rename dest to `"plan_number"`, help text `"Plan issue number"` → `"Plan number"`
- Line 54: Function parameter `issue_number: int` → `plan_number: int`
- Line 103: `issues.add_comment(repo_root, issue_number, comment_body)` → `issues.add_comment(repo_root, plan_number, comment_body)`

**Note**: The CLI flag name `--issue` can remain as-is since it's short and the help text clarifies it refers to a plan. However, for consistency with the rename, change the Click option's Python variable destination from `issue_number` to `plan_number`.

### 6. `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

**Rename `plan_issue_number` → `plan_number`:**

This file already uses `plan_issue_number` (not bare `issue_number`). Rename to `plan_number` for consistency:

- Line 134: Comment `# Objective issue number if marker exists` — leave as-is (refers to objective, not plan)
- Line 140: Field `plan_issue_number: int | None` → `plan_number: int | None`, update comment `# Issue number from .impl/issue.json` → `# Plan number from .impl/plan-ref.json`
- Line 159: Parameter `plan_issue_number: int | None = None,` → `plan_number: int | None = None,`
- Line 174: Docstring `- plan_issue_number: None` → `- plan_number: None`
- Line 190: `plan_issue_number=plan_issue_number,` → `plan_number=plan_number,`
- Line 254: Function parameter `plan_issue_number: int | None,` → `plan_number: int | None,`
- Line 268: Docstring `plan_issue_number: Issue number from .impl/issue.json.` → `plan_number: Plan number from .impl/plan-ref.json.`
- Line 286-287: `if plan_issue_number is not None:` → `if plan_number is not None:` and `f"plan:#{plan_issue_number}"` → `f"plan:#{plan_number}"`
- Line 459: `plan_issue_number=hook_input.plan_issue_number,` → `plan_number=hook_input.plan_number,`
- Line 664: `plan_issue_number: int | None = None` → `plan_number: int | None = None`
- Line 679-681: `plan_issue_number = (int(plan_ref.plan_id)…)` → `plan_number = (int(plan_ref.plan_id)…)`
- Line 700: `plan_issue_number=plan_issue_number,` → `plan_number=plan_number,`

### 7. `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py`

**Rename `issue_number` → `plan_number`:**
- Line 4: Docstring `erk exec close-issue-with-comment <ISSUE_NUMBER>` → `erk exec close-issue-with-comment <PLAN_NUMBER>`
- Line 7: Docstring `JSON with {success, issue_number, comment_id}` → `JSON with {success, plan_number, comment_id}`
- Line 25: Click argument `@click.argument("issue_number", type=int)` → `@click.argument("plan_number", type=int)`
- Line 34: Function parameter `issue_number: int` → `plan_number: int`
- Line 41: `plan_id = str(issue_number)` → `plan_id = str(plan_number)`
- Line 51: Error message `f"Failed to add comment to issue #{issue_number}: {e}"` → `f"Failed to add comment to plan #{plan_number}: {e}"`
- Line 65: Error message `f"Failed to close issue #{issue_number}: {e}"` → `f"Failed to close plan #{plan_number}: {e}"`
- Line 76: JSON key `"issue_number": issue_number` → `"plan_number": plan_number`

### 8. `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py`

**Rename `issue_number` → `plan_number`:**
- Line 8: Docstring `erk exec track-learn-evaluation <issue-number>` → `erk exec track-learn-evaluation <plan-number>`
- Line 14: Docstring `"issue_number": 123` → `"plan_number": 123`
- Line 47: Dataclass field `issue_number: int` → `plan_number: int`
- Line 60: Function name `_extract_issue_number` → `_extract_plan_number`
- Line 61: Parameter doc updates
- Line 86: Parameter `issue_number: int` → `plan_number: int`
- Line 95: Docstring `issue_number: Plan issue number` → `plan_number: Plan number`
- Line 105: `str(issue_number),` → `str(plan_number),`
- Line 116: `str(issue_number),` → `str(plan_number),`
- Line 127: `f"Plan {issue_number} has no plan-header…"` → `f"Plan {plan_number} has no plan-header…"`
- Line 137: Error message `f"Failed to track learn evaluation on issue #{issue_number}: {e}"` → `f"Failed to track learn evaluation on plan #{plan_number}: {e}"`
- Line 167: Variable `issue_number: int | None = None` → `plan_number: int | None = None`
- Line 169: `issue_number = _extract_issue_number(issue)` → `plan_number = _extract_plan_number(issue)`
- Line 170: `if issue_number is None:` → `if plan_number is None:`
- Line 184: `issue_number = int(plan_id_str)` → `plan_number = int(plan_id_str)`
- Line 186: `if issue_number is None:` → `if plan_number is None:`
- Line 189: Error `"no-issue-specified"` → `"no-plan-specified"`
- Line 190: Message `"No issue specified…"` → `"No plan specified…"`
- Line 199: `issue_number=issue_number` → `plan_number=plan_number`
- Line 206: `issue_number=issue_number` → `plan_number=plan_number`

### 9. `src/erk/cli/commands/exec/scripts/get_closing_text.py`

**Comment-only updates (no `issue_number` variables in this file):**
- Line 62: Comment `can't determine issue number` → `can't determine plan number`
- Line 78: Comment `No issue to close` → `No plan to close`

### 10. `src/erk/cli/commands/exec/scripts/get_pr_body_footer.py`

**Rename `issue_number` → `plan_number`:**
- Line 9: Docstring `--issue-number 456` → `--plan-number 456`
- Line 29: Docstring `--issue-number 123` → `--plan-number 123`
- Line 49: Click option `--issue-number` → `--plan-number`, help `"Issue number to close"` → `"Plan number to close"`
- Line 53: Function parameter `issue_number: int | None` → `plan_number: int | None`
- Line 59: Docstring `When issue_number is provided` → `When plan_number is provided`
- Line 64: Docstring `issue_number: Optional issue number to close` → `plan_number: Optional plan number to close`
- Line 68: `build_pr_body_footer(pr_number=pr_number, issue_number=issue_number, plans_repo=plans_repo)` → `build_pr_body_footer(pr_number=pr_number, issue_number=plan_number, plans_repo=plans_repo)` — **Note**: Keep `issue_number=` keyword since `build_pr_body_footer` callee is out of scope (phase 7). Pass the renamed local variable `plan_number` as the value.

### 11. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`

**Rename `issue_number` → `plan_number` in internal functions only:**
- Line 138: Parameter `issue_number: int | None,` → `plan_number: int | None,`
- Line 148: Docstring `issue_number: Issue number to close on merge` → `plan_number: Plan number to close on merge`
- Line 164: `build_pr_body_footer(pr_number=pr_number, issue_number=issue_number, plans_repo=plans_repo)` → `build_pr_body_footer(pr_number=pr_number, issue_number=plan_number, plans_repo=plans_repo)` — **Note**: Keep `issue_number=` keyword since callee is out of scope.
- Line 176: Parameter `issue_number: int,` → `plan_number: int,`
- Line 189: Docstring `issue_number: Issue number to close on merge` → `plan_number: Plan number to close on merge`
- Line 289: `issue_number=None,` → `plan_number=None,` (local call to `_build_pr_body`)
- Line 299: `issue_number=issue_number,` → `plan_number=plan_number,` (local call)
- Line 357: `issue_number=plan_id,` → `plan_number=plan_id,` (local call)

### 12. `src/erk/cli/commands/exec/scripts/update_pr_description.py`

**Rename call-site parameter:**
- Line 151: `issue_number=None,` → This calls `assemble_pr_body` which is in `pr/shared.py` (phase 6 scope). **Keep `issue_number=None`** since the callee still uses `issue_number`. No changes in this file for phase 4.1.

**Re-evaluation**: On closer inspection, `update_pr_description.py` has only one `issue_number` reference (line 151) and it's a keyword argument to an out-of-scope callee. **No changes needed in this file for phase 4.1.**

## Caller Updates (Commands and Workflows)

These callers parse JSON output from the renamed scripts and need key name updates:

### `.claude/commands/erk/one-shot-plan.md`

This file instructs Claude to parse JSON output. The one-shot-plan command references `plan-save` and `plan-update-issue` JSON keys. Check and update references to `issue_number`/`issue_url` if present. (Note: `plan-save` was already renamed in phase 2, so its callers may already be correct.)

### `.claude/commands/erk/learn.md`

Update lines that reference parsing `issue_number` and `issue_url` from exec command JSON output to use `plan_number` and `plan_url`.

### `.github/workflows/one-shot.yml`

Update any references to `--issue-number` flags passed to `register-one-shot-plan` to use `--plan-number`.

### `.github/workflows/plan-implement.yml`

Check for `--issue-number` references to `register-one-shot-plan`, `get-pr-body-footer`, `get-plan-metadata`, and update flags.

## Files NOT Changing

- **`packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py`** — `build_pr_body_footer` function signature stays `issue_number` (phase 7)
- **`src/erk/cli/commands/pr/shared.py`** — `assemble_pr_body` stays `issue_number` (phase 6)
- **`src/erk/cli/commands/pr/metadata_helpers.py`** — `write_dispatch_metadata` stays `issue_number` (phase 6)
- **`src/erk/cli/commands/exec/scripts/update_pr_description.py`** — Only reference is keyword arg to out-of-scope callee
- **`update_dispatch_info.py`** — Does not exist in the codebase
- **Test files** — Tests are phase 4.2 scope

## Implementation Details

### Pattern to follow

Follow the established pattern from phases 1–3:

1. **Local variables and parameters**: `issue_number` → `plan_number`
2. **Click arguments**: `@click.argument("issue_number")` → `@click.argument("plan_number")`
3. **Click options**: `--issue-number` → `--plan-number`
4. **JSON output keys**: `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"`
5. **Dataclass fields**: `issue_number: int` → `plan_number: int`
6. **Error messages**: `"Issue #N"` → `"Plan #N"`
7. **Error codes**: `"no-issue-specified"` → `"no-plan-specified"`, `"issue_not_found"` → `"plan_not_found"`
8. **Comments**: Update to use plan terminology
9. **Docstrings**: Update usage examples and parameter descriptions

### Cross-boundary calls (IMPORTANT)

When a renamed local variable is passed to an out-of-scope function that still uses `issue_number` in its signature, **keep the keyword argument name matching the callee**:

```python
# CORRECT: local var renamed, keyword matches callee's current signature
build_pr_body_footer(pr_number=pr_number, issue_number=plan_number, plans_repo=plans_repo)
write_dispatch_metadata(..., issue_number=plan_number, ...)
```

This avoids breaking callee signatures that will be renamed in later phases.

### Function rename

In `track_learn_evaluation.py`, rename the helper function:
- `_extract_issue_number()` → `_extract_plan_number()`

### Error sentinel values

Rename error sentinel strings for consistency:
- `"no-issue-specified"` → `"no-plan-specified"` (track_learn_evaluation.py)
- `"issue_not_found"` → `"plan_not_found"` (get_plan_metadata.py)

## Verification

1. Run `ruff check` and `ruff format` on all modified files
2. Run `ty` type checker
3. Grep for remaining `issue_number` in the 12 modified files to confirm no occurrences remain (except cross-boundary keyword arguments)
4. Run the unit test suite (tests may need updates in phase 4.2, but existing tests should surface breakage)