# Plan: Phase 4 — Fix CLI Help, Output Messages, Docstrings (Objective #8381)

## Context

Objective #8381 standardizes "plan-as-PR" terminology. Phase 1 landed (PR #8382), Phase 3 dispatched (#8385). This plan covers **Phase 4 (nodes 4.1-4.6)**: fixing Python source code in `src/erk/` — Click help strings, user-facing output messages, URL constructions, module docstrings, and TUI notifications.

Unlike Phase 3 (prose-only in markdown), Phase 4 touches actual Python code. Changes must pass CI (ruff, ty, pytest).

## Constraint: What NOT to Change

These are internal identifiers renamed in later phases (5, 7):
- Variable/parameter names: `issue_number`, `issue_refs`, `objective_issue`, `plan_id` (when used as variable)
- Function names: `get_issues_with_pr_linkages()`, `action_open_issue()`
- Class names: `IssuePlanSource`, `IssueNextSteps`
- CLI flag names: `--issue` (on `setup-impl` and others — Phase 5)
- JSON output field names: `issue_number` (Phase 5)
- Error codes: `"issue-not-found"` (Phase 5)

**Only change**: help text strings, user-facing output strings, docstrings, URL construction patterns.

## Changes by Node

### Node 4.1: Click `help=` Strings (6 files, ~8 changes)

**`src/erk/cli/commands/branch/create_cmd.py`** (line 40):
- `help="GitHub issue number or URL with erk-plan label"` → `help="Plan number or URL with erk-plan label"`

**`src/erk/cli/commands/branch/checkout_cmd.py`** (line 341):
- `help="GitHub issue/PR number with erk-plan label"` → `help="Plan number or PR with erk-plan label"`

**`src/erk/cli/commands/admin.py`** (line 419):
- `help="Existing plan issue number to use"` → `help="Existing plan number to use"`

**`src/erk/cli/commands/wt/create_cmd.py`** (line 453):
- `help="GitHub issue number or URL with erk-plan label. Fetches issue content..."` → `help="Plan number or URL with erk-plan label. Fetches plan content..."`

**`src/erk/cli/commands/pr/list_cmd.py`** (lines 112-114):
- `click.Choice(["issue", "activity"])` → `click.Choice(["plan", "activity"])`
- `default="issue"` → `default="plan"`
- `help="Sort order: by issue number (default)..."` → `help="Sort order: by plan number (default)..."`
- Also update any code that checks `sort == "issue"` to check `sort == "plan"`

**`src/erk/cli/commands/learn/learn_cmd.py`** (line 63):
- `@click.argument("issue", ...)` → `@click.argument("plan", ...)`
- Update function parameter and all internal references to match

### Node 4.2: User-Facing Output Messages (~22 changes across ~13 files)

**`src/erk/cli/commands/admin.py`**:
- Line 462: `"Using existing issue #{plan_number}"` → `"Using existing plan #{plan_number}"`
- Line 471: `"Created test issue #{plan_number}"` → `"Created test plan #{plan_number}"`

**`src/erk/cli/commands/objective_helpers.py`**:
- Lines 46, 51: `"Closed plan issue #{plan_number}"` → `"Closed plan #{plan_number}"`

**`src/erk/cli/commands/learn/learn_cmd.py`**:
- Line 113: `"Invalid issue identifier"` → `"Invalid plan identifier"`
- Line 122: `"No issue specified"` → `"No plan specified"`
- Line 124: `"erk learn <issue-number>"` → `"erk learn <plan-number>"`

**`src/erk/cli/commands/pr/check_cmd.py`**:
- Line 95: `"Issue #{plan_number} not found"` → `"Plan #{plan_number} not found"`

**`src/erk/cli/commands/pr/view_cmd.py`**:
- Line 273: `"Issue #{plan_id} not found"` → `"Plan #{plan_id} not found"`

**`src/erk/cli/commands/pr/create_cmd.py`**:
- Line 116: `"Issue: {result.plan_url}"` → `"Plan: {result.plan_url}"`

**`src/erk/cli/commands/wt/create_cmd.py`**:
- Line 673: `"Issue #{plan_number_parsed} not found"` → `"Plan #{plan_number_parsed} not found"`
- Line 932: `"Created worktree from issue #{setup.plan_number}"` → `"Created worktree from plan #{setup.plan_number}"`

**`src/erk/cli/commands/exec/scripts/plan_update.py`**:
- Line 110: `"Issue #{plan_number} not found"` → `"Plan #{plan_number} not found"`
- Line 151: `"Plan updated on issue #{plan_number}"` → `"Plan #{plan_number} updated"`

**`src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py`**:
- Line 80: `"Issue #{plan_number} not found"` → `"Plan #{plan_number} not found"`

**`src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`**:
- Line 221: `"Objective issue #{objective_number} not found"` → `"Objective #{objective_number} not found"`

**`src/erk/cli/github_parsing.py`**:
- Line 60: `"Invalid issue number or URL"` → `"Invalid plan number or URL"`

### Node 4.3: Hardcoded `/issues/` URL Constructions (2 files + 1 parser)

**`src/erk/cli/commands/pr/submit_pipeline.py`** (line 165):
- `f"https://github.com/{owner}/{repo_name}/issues/{plan_id}"` → `f"https://github.com/{owner}/{repo_name}/pull/{plan_id}"`
- Context: auto-repair for plan-ref.json. New plans are draft PRs.

**`src/erk/cli/commands/run/list_cmd.py`** (line 135):
- `f"https://github.com/...issues/{plan_num}"` → `f"https://github.com/...pull/{plan_num}"`

**`src/erk/tui/app.py`** (line 71) — URL parser:
- `plan_url.rsplit("/issues/", 1)[0]` — must handle both `/pull/` and `/issues/` for backwards compat
- Change to: try `/pull/` first, fall back to `/issues/`

### Node 4.4: CLI Module Docstrings (4 files)

**`src/erk/cli/commands/pr/create_cmd.py`** (line 1):
- `"create a plan issue from markdown content"` → `"create a plan from markdown content"`

**`src/erk/cli/commands/pr/replan_cmd.py`** (lines 1, 10, 13, 16):
- Module docstring: `"erk-plan issue(s)"` → `"plan(s)"`
- Function docstring: `"erk-plan issue(s)"` → `"plan(s)"`
- `"ISSUE_REFS are issue numbers"` → `"ISSUE_REFS are plan numbers"`

**`src/erk/cli/commands/implement.py`** (line 1):
- `"from GitHub issues or plan files"` → `"from plans or plan files"`

**`src/erk/cli/commands/land_learn.py`** (lines 1-4):
- `"Learn issue creation"` → `"Learn plan creation"`
- `"creating erk-learn plan issues"` → `"creating erk-learn plans"`

### Node 4.5: Core Module Docstrings (3 files need changes)

**`src/erk/core/plan_context_provider.py`** (line 3):
- `"linked to erk-plan issues"` → `"linked to plans"`

**`src/erk/core/branch_slug_generator.py`** (line 4):
- `"plan/issue titles"` → `"plan titles"`

**`src/erk/core/services/plan_list_service.py`** (lines 4, 7):
- `"All plan issues store"` → `"All plans store"`
- Leave function name reference `get_issues_with_pr_linkages()` as-is (Phase 7)

### Node 4.6: TUI Output (3 changes in 1 file)

**`src/erk/tui/app.py`**:
- Line 1173: `"Opened issue #{row.plan_id}"` → `"Opened plan #{row.plan_id}"`
- Line 1346: `"Opened issue #{row.plan_id}"` → `"Opened plan #{row.plan_id}"`
- Line 1391: `"Opened issue {display}"` → `"Opened plan {display}"`

## Verification

1. **Grep for remaining stale strings**: `grep -rn '".*[Ii]ssue.*#' src/erk/` — verify remaining hits are objective issues or internal identifiers
2. **CI**: Run `make fast-ci` (ruff lint, ruff format, ty check, unit tests)
3. **Grep for sort choice**: Verify no code still checks `sort == "issue"` after the list_cmd change
4. **URL construction**: Verify no other `/issues/` URL constructions exist: `grep -rn '/issues/' src/erk/ --include='*.py'` — remaining hits should be GitHub API calls or comment/issue operations

## Execution Order

1. Node 4.4 + 4.5 (docstrings — lowest risk, no behavioral change)
2. Node 4.1 (Click help strings — low risk, cosmetic)
3. Node 4.2 (output messages — medium risk, user-visible strings)
4. Node 4.3 (URL constructions — highest risk, behavioral change)
5. Node 4.6 (TUI notifications — low risk)
6. Verification: grep + CI
