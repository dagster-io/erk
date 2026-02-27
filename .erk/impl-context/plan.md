# Plan: Complete objective #7724 — Rename issue_number to plan_number (nodes 9.2, 9.4, 9.5)

Part of Objective #7724, Nodes 9.2 + 9.4 + 9.5

## Context

Objective #7724 renames `issue_number` to `plan_number` across all plan-related code. 21 of 24 nodes are done. Three remain — all in the erk-shared and erk-statusline packages. These are combined into a single PR since they're tightly coupled: renaming production code (9.2, 9.4) requires updating tests (9.5) in the same change to keep CI green.

## Key Design Decision: What NOT to Rename

The gateway `issues/` module has generic GitHub operations that work with ANY issue (plans, objectives, PRs). These `issue_number` parameters are semantically correct and must be KEPT:

- `ensure_label_on_issue(issue_number)` — generic label operation
- `remove_label_from_issue(issue_number)` — generic label operation
- `IssueNotFound.issue_number` — generic sentinel type
- `FakeGitHubIssues.next_issue_number` — generic auto-increment counter
- `FakeGitHubIssues._added_comments` tuples with issue numbers — generic tracking
- `GitHubChecks.issue_comments(issue_number)` — generic PR/issue comment retrieval

## Implementation

### Step 1: Node 9.2 — Gateway ABCs/Implementations (plan-specific methods only)

**`packages/erk-shared/src/erk_shared/gateway/github/abc.py`**
- `get_prs_linked_to_issues()`: rename param `issue_numbers` → `plan_numbers` (line 197), update docstring (lines 207, 210)
- `get_issues_by_numbers_with_pr_linkages()`: rename param `issue_numbers` → `plan_numbers` (line 750), update docstring (lines 760, 765)

**`packages/erk-shared/src/erk_shared/gateway/github/real.py`**
- Same two methods: rename `issue_numbers` → `plan_numbers` in signatures
- Internal variables in implementations: rename loop vars and dict keys from `issue_number`/`issue_num` → `plan_number`/`plan_num` where they refer to plan numbers

**`packages/erk-shared/src/erk_shared/gateway/github/fake.py`**
- Same two methods: rename `issue_numbers` → `plan_numbers`
- `pr_issue_linkages` docstring/constructor param → `pr_plan_linkages`
- Internal loop vars that shadow the plan number

**`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`**
- Same two methods: rename `issue_numbers` → `plan_numbers` in delegation

**`packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py`**
- `get_prs_referencing_issue()`: rename param `issue_number` → `plan_number` (line 272), update docstring (line 283)

**`packages/erk-shared/src/erk_shared/gateway/github/issues/real.py`**
- `get_prs_referencing_issue()`: rename param `issue_number` → `plan_number`, update internal vars

**`packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py`**
- `get_prs_referencing_issue()`: rename param `issue_number` → `plan_number`

**`packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py`**
- `get_prs_referencing_issue()`: rename param `issue_number` → `plan_number`

### Step 2: Node 9.2 — Cross-boundary callers

These callers use keyword args with the old parameter name:

**`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py:447`**
- `issue_numbers=list(plan_ids)` → `plan_numbers=list(plan_ids)`

**`packages/erk-shared/src/erk_shared/gateway/github/printing.py`** (if it wraps these methods)
- Update delegation params

**`src/erk/cli/commands/run/list_cmd.py:93`**
- Already uses variable `plan_numbers`, just update keyword: `issue_numbers=` → `plan_numbers=`

### Step 3: Node 9.4 — Metadata files

**`packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`**
- `create_submission_queued_block(issue_number)` → `plan_number` (line 269), update docstring + data dict key
- `create_workflow_started_block(issue_number)` → `plan_number` (line 308), update docstring + data dict key
- `format_execution_commands(issue_number)` → `plan_number` (line 399), update docstring
- `format_plan_commands_section(issue_number)` → `plan_number` (line 412), update docstring
- `format_plan_issue_body(issue_number)` → `plan_number` (line 449), update docstring + internal usage

**`packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`**
- `SubmissionQueuedSchema`: rename `"issue_number"` → `"plan_number"` in required fields (line 148) and validation (lines 184-188)
- Add backward-compat migration (same pattern as lines 45-46): `if "issue_number" in data and "plan_number" not in data: data["plan_number"] = data.pop("issue_number")`
- `WorkflowStartedSchema`: same changes (lines 209, 238-242)

**`packages/erk-shared/src/erk_shared/gateway/github/parsing.py`**
- Rename function `parse_issue_number_from_url()` → `parse_plan_number_from_url()` (line 222)
- Update docstring examples (lines 234, 236)
- `construct_issue_url()`: rename param `issue_number` → `plan_number` (line 304), update docstring + f-string

**`packages/erk-shared/src/erk_shared/gateway/gt/types.py`**
- `PreAnalysisResult.issue_number` → `plan_number` (line 156), update comment

**`packages/erk-shared/src/erk_shared/gateway/github/checks.py`** — NO CHANGES (generic operation)

**`packages/erk-shared/src/erk_shared/gateway/github/issues/types.py`** — NO CHANGES (`IssueNotFound.issue_number` is generic)

### Step 4: Node 9.4 — Cross-boundary callers

**`src/erk/cli/commands/pr/dispatch_cmd.py:347`**
- `issue_number=plan_number` → `plan_number=plan_number`

**`src/erk/cli/commands/one_shot_dispatch.py:374`**
- `issue_number=plan_number` → `plan_number=plan_number`

**`src/erk/cli/commands/exec/scripts/create_plan_from_context.py:100`**
- Uses positional args: `format_plan_issue_body(plan.strip(), result.number, url=result.url)` — safe, no keyword change needed

**Callers of `parse_issue_number_from_url`** — grep and update all import sites to `parse_plan_number_from_url`

**Callers of `PreAnalysisResult.issue_number`** — grep and update all access sites to `.plan_number`

### Step 5: Node 9.4 — Statusline package

**`packages/erk-statusline/src/erk_statusline/statusline.py`**
- Rename function `get_issue_number()` → `get_plan_number()` (line 238), update docstring
- Keep legacy `data.get("issue_number")` read inside (line 260) — backward compat for old `.impl/issue.json`
- Rename `build_gh_label(issue_number=)` → `build_gh_label(plan_number=)` (line 1077), update docstring + internal usage (lines 1099, 1103)
- Update caller at line 1253: `issue_number=issue_number` → `plan_number=plan_number`
- Rename local variable at line 1187 and 1205: `issue_number` → `plan_number`

### Step 6: Node 9.5 — erk-shared tests

**`packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py`**
- 5 occurrences: `"issue_number": 42` → `"plan_number": 42` in JSON test fixtures

**`packages/erk-shared/tests/unit/github/test_parsing.py`**
- Update import: `parse_issue_number_from_url` → `parse_plan_number_from_url`
- Rename all test functions and assertions (~11 occurrences)

**`packages/erk-shared/tests/unit/output/test_next_steps.py`**
- 2 occurrences: `IssueNextSteps(issue_number=99` → `IssueNextSteps(plan_number=99` (if class field renamed) or update keyword

**`packages/erk-shared/tests/unit/github/test_pr_footer.py`**
- ~8 occurrences: `issue_number=` keyword in `build_pr_body_footer()` calls → `plan_number=`
- Test function names containing "issue_number" → "plan_number"

**`packages/erk-shared/tests/unit/github/test_plan_issues.py`**
- Line 941: test name `test_commands_section_uses_correct_issue_number` → `test_commands_section_uses_correct_plan_number`
- Line 943: `next_issue_number=42` — KEEP (this is generic `FakeGitHubIssues` constructor param)

**`packages/erk-shared/tests/unit/scratch/test_session_markers.py`**
- Line 74: test name update

### Step 7: Node 9.5 — erk-statusline tests

**`packages/erk-statusline/tests/test_statusline.py`** (~32 occurrences)
- Update import: `get_issue_number` → `get_plan_number`
- Rename `TestGetIssueNumber` class → `TestGetPlanNumber`
- Update all test method names containing "issue_number"
- Update `build_gh_label(..., issue_number=...)` → `plan_number=`
- Keep `"issue_number"` in JSON test fixtures that test legacy backward compat reading (e.g., `test_valid_issue_json_with_issue_number_key`)

## Verification

1. Run `make fast-ci` — unit tests, linting, type checking
2. Run `make all-ci` — full test suite including integration tests
3. Grep for remaining `issue_number` in erk-shared/erk-statusline src/ to confirm only generic references remain
4. Verify cross-boundary callers compile: `ty check` on full project
