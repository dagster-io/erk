# Plan: Rename plan_number/plan_id params across gateway layer (Objective #9109, Node 5.2)

## Context

Part of **Objective #9109**, Node 5.2: Rename "plan" terminology to "pr" across all APIs.

Phase 5 focuses on renaming internal parameters/variables that still use `plan_number` or `plan_id` after the type/class renames in phases 1-4. Node 5.1 (PR #9198) renamed the plan_store ABC classes and methods. This node targets the gateway layer: metadata serialization, command executor, issues, objective_issues, parsing, and GitHub ABC/implementations.

**Pattern from prior nodes:** Immediate rename with no backwards-compatibility shims. Tests are deferred to node 7.2.

## Scope

All files are in `packages/erk-shared/src/erk_shared/gateway/`. The rename is purely mechanical — parameter names, variable names, dict keys, docstrings, and function names. No behavioral changes.

### YAML Serialization Key (metadata/core.py)

The serialized YAML key `plan_number` in metadata blocks must change to `pr_number`. The migration helper in `schemas.py` already handles reading legacy `plan_number` keys, so old metadata remains readable.

## Files to Modify

### 1. `gateway/github/metadata/core.py` (~6 functions)

Rename `plan_number` parameter to `pr_number` in:
- `create_worktree_creation_block()` (line 203) — param + dict key `data["plan_number"]` → `data["pr_number"]` + docstring
- `create_plan_block()` (line 239) — param + dict key + docstring
- `create_submission_queued_block()` (line 276) — param + dict key + docstring
- `create_workflow_started_block()` (line 315) — param + dict key + docstring
- `format_execution_commands()` (line 406) — param + docstring
- `format_plan_commands_section()` (line 419) — param + docstring
- `format_plan_issue_body()` (line 456) — param + docstring

### 2. `gateway/command_executor/abc.py` (~2 methods)

Rename `plan_id` → `pr_number` and `plan_url` → `pr_url` in:
- `close_plan()` (line 32) — param + docstring
- `dispatch_to_queue()` (line 60) — param + docstring

### 3. `gateway/command_executor/real.py` (~4 callsites)

Rename to match ABC changes:
- `__init__()` params: `close_plan_fn` → `close_pr_fn`, `dispatch_to_queue_fn` stays (already generic)
  - `self._close_plan_fn` → `self._close_pr_fn` + docstring
- `close_plan()` (line 56) — `plan_id` → `pr_number`, `plan_url` → `pr_url`
- `dispatch_to_queue()` (line 68) — `plan_id` → `pr_number`, `plan_url` → `pr_url`

### 4. `gateway/github/issues/abc.py` (~1 method)

- `get_prs_referencing_issue()` (line 272) — `plan_number` → `pr_number` + docstring

### 5. `gateway/github/issues/dry_run.py` (~1 method)

- `get_prs_referencing_issue()` (line 114) — `plan_number` → `pr_number`

### 6. `gateway/github/issues/real.py` (~1 method)

- `get_prs_referencing_issue()` (line 557) — `plan_number` → `pr_number`

### 7. `gateway/github/objective_issues.py` (~1 field + 6 constructor calls)

- `CreateObjectiveIssueResult.plan_number` (line 67) → `pr_number` + docstring
- Update all 6 `CreateObjectiveIssueResult(plan_number=...)` calls to `pr_number=...`

### 8. `gateway/github/parsing.py` (~2 items)

- Rename function `parse_plan_number_from_url()` (line 227) → `parse_issue_number_from_url()` — this function parses `/issues/` URLs; the companion `parse_pr_number_from_url` handles `/pull/` URLs. Both are needed and used side-by-side in `checkout_cmd.py` and `github_parsing.py` to distinguish URL types. Update docstring accordingly.
- `construct_issue_url()` (line 309) — rename param `plan_number` → `issue_number` + docstring

### 9. `gateway/github/abc.py` (~2 methods + docstrings)

- `get_prs_linked_to_issues()` (line 251) — `plan_numbers` → `pr_numbers` + docstring
- `get_issues_by_numbers_with_pr_linkages()` (line 885) — `plan_numbers` → `pr_numbers` + docstring
- Docstring on line 444: `plan_number` → `pr_number`

### 10. `gateway/github/dry_run.py` (~2 methods)

- `get_prs_linked_to_issues()` (line 139) — `plan_numbers` → `pr_numbers`
- `get_issues_by_numbers_with_pr_linkages()` (line 395) — `plan_numbers` → `pr_numbers`

### 11. `gateway/github/real.py` (~multiple methods)

- `get_prs_linked_to_issues()` (line 758) — `plan_numbers` → `pr_numbers` + internal vars
- `_build_issue_pr_linkage_query()` (line 787) — `plan_numbers` → `pr_numbers` + docstring + loop var `plan_num` → `pr_num`
- `_parse_issue_pr_linkages()` (line 856) — local var `plan_number` → `pr_number`
- `get_issues_by_numbers_with_pr_linkages()` (line 2552) — `plan_numbers` → `pr_numbers`
- `_build_issues_by_numbers_query()` (line 2566) — `plan_numbers` → `pr_numbers` + loop var

## Callers to Update (outside gateway, in src/erk/)

These files pass the renamed parameters by keyword and must be updated:

- `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py` — `result.plan_number` → `result.pr_number` (5 occurrences)
- `src/erk/cli/github_parsing.py` — import `parse_plan_number_from_url` → `parse_issue_number_from_url` + callsite
- `src/erk/cli/commands/pr/checkout_cmd.py` — import + callsite for `parse_plan_number_from_url`
- `src/erk/cli/commands/exec/scripts/resolve_objective_ref.py` — import + callsite for `parse_plan_number_from_url`
- `src/erk/cli/commands/run/list_cmd.py` — kwarg `plan_numbers` → `pr_numbers`
- `src/erk/tui/data/real_provider.py` — kwarg `plan_numbers` → `pr_numbers` (2 calls)
- `src/erk/tui/actions/navigation.py` — kwarg `close_plan_fn` → `close_pr_fn`

## Out of Scope (deferred to later nodes)

- **Test updates** — deferred to node 7.2 (test fixtures/assertions for phases 5-6)
- **CLI/TUI internal variables** — deferred to node 6.1
- **Method names** (`close_plan`, `dispatch_to_queue`) — these are method names, not parameter names; renaming them would cascade into TUI and is better handled in node 6.1

## Implementation Order

1. Start with the gateway ABC files (abc.py files define the contract)
2. Update implementations (real.py, dry_run.py)
3. Update dataclass fields (objective_issues.py CreateObjectiveIssueResult)
4. Update metadata/core.py (YAML keys + params)
5. Update parsing.py (function rename + param rename)
6. Update all callers in src/erk/

## Verification

1. `ruff check` — ensure no import errors or undefined names
2. `ty check` — type checking passes
3. `grep -r "plan_number\|plan_id" packages/erk-shared/src/erk_shared/gateway/` — verify no remaining references (except `_migrate_to_pr_number` which intentionally handles legacy `plan_number` keys)
4. `make fast-ci` — unit tests pass (some test files may need updates for import renames, handle as encountered)
