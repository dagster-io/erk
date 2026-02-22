# Plan: Rename issue_number to plan_number in impl_* exec scripts

Part of Objective #7724, Node 3.1

## Context

Objective #7724 renames `issue_number` to `plan_number` across the codebase to better reflect that these references point to *plans*, not generic GitHub issues. Phases 1-2 are complete (PR #7849, #7896). This plan covers Phase 3's source file renames (node 3.1); tests are covered by node 3.2.

## Scope

6 source files, ~50 occurrences total. No test files (node 3.2). No callers (nodes 4.x-8.x).

## Changes by File

### 1. `src/erk/cli/commands/exec/scripts/impl_init.py` (3 occurrences)
- Line 138: `issue_number` local variable → `plan_number`
- Line 155-156: `result["issue_number"]` → `result["plan_number"]`
- Line 21: Docstring example JSON key update

### 2. `src/erk/cli/commands/exec/scripts/impl_signal.py` (7 occurrences)
- Line 64: `SignalSuccess.issue_number` dataclass field → `plan_number`
- Lines 276, 355, 418: Constructor args `issue_number=` → `plan_number=`
- Lines 25, 28, 31: Docstring example JSON key updates

### 3. `src/erk/cli/commands/exec/scripts/check_impl.py` (6 occurrences)
- Line 68: `_get_issue_reference()` → `_get_plan_reference()`
- Line 76: Docstring `issue_number and issue_url` → `plan_number and plan_url`
- Line 90: `"issue_number"` dict key → `"plan_number"`
- Line 91: `"issue_url"` dict key → `"plan_url"`
- Lines 95, 100, 138: `issue_info` variable → `plan_info` (all occurrences)
- Lines 103, 120: `issue_info['issue_number']` → `plan_info['plan_number']`
- Line 146: `"has_issue_tracking"` dict key → `"has_plan_tracking"` (aligns with rename intent)

**Note on `has_issue_tracking`**: This key appears in JSON output at line 146. The prior phases renamed similar keys. Rename to `has_plan_tracking` for consistency. Also rename the `has_issue_tracking` local variable at line 137.

### 4. `src/erk/cli/commands/exec/scripts/mark_impl_started.py` (5 occurrences)
- Line 49: `MarkImplSuccess.issue_number` dataclass field → `plan_number`
- Line 168: Constructor arg `issue_number=` → `plan_number=`
- Lines 22, 25: Docstring example JSON key updates

### 5. `src/erk/cli/commands/exec/scripts/mark_impl_ended.py` (5 occurrences)
- Line 49: `MarkImplSuccess.issue_number` dataclass field → `plan_number`
- Line 164: Constructor arg `issue_number=` → `plan_number=`
- Lines 22, 25: Docstring example JSON key updates

### 6. `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (24 occurrences)
- Line 375: Click argument `"issue_number"` → `"plan_number"`
- Line 389: Function param `issue_number: int` → `plan_number: int`
- Lines 120, 257: `_setup_draft_pr_plan` and `_setup_issue_plan` params `issue_number: int` → `plan_number: int`
- All internal uses of the `issue_number` variable → `plan_number` (~18 sites)
- JSON output keys: `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"` (3 return dicts)
- Line 18: Docstring example JSON key update
- Lines 411, 413: Keyword args `issue_number=issue_number` → `plan_number=plan_number`

## Approach

Use `Edit` with `replace_all=true` for bulk variable renames within each file. Handle JSON key renames and function renames with targeted edits where `replace_all` could cause false positives.

Order: simplest files first (impl_init → mark_impl_started → mark_impl_ended → impl_signal → check_impl → setup_impl_from_issue).

## Verification

1. Run `ruff check` on all 6 files (via devrun agent)
2. Run `ty check` on all 6 files (via devrun agent)
3. Grep to confirm zero remaining `issue_number` occurrences in the 6 files
4. Run existing tests for these scripts (via devrun agent) to catch regressions — tests will need updating in node 3.2 but should reveal if any test currently passes and we've broken the interface
