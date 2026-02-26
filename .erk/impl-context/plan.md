# Documentation Plan: Re-add plan field to RoadmapNode/ObjectiveNode and fix objective head column

## Context

This implementation fixed critical bugs in the objectives dashboard's head column that was always displaying "-" (blank) for all objectives. The root cause was multifaceted: missing `in_progress` status handling, inconsistent status formatting (spaces vs hyphens), wrong URL paths for GitHub PRs (`/issues/` instead of `/pull/`), and inline logic that was difficult to test. The implementation extracted the head state computation into a standalone testable function, corrected URL construction patterns, and established a workflow improvement where plan issue numbers populate the roadmap node's `pr` field immediately upon plan creation.

The sessions also uncovered significant documentation debt: five existing docs still referenced a `plan` field on RoadmapNode/ObjectiveNode that was removed in commit 3be1ad48e. This stale documentation describes code that no longer exists and must be cleaned up before adding new documentation to avoid compounding confusion.

A key architectural insight emerged: when extracting logic from high-level modules like `real.py`, the function should be placed in low-level modules like `dependency_graph.py` to avoid circular imports during testing. The agent encountered and resolved a circular import chain (real.py -> erk.core.context -> CLI -> dash_data.py -> real.py) by moving `compute_objective_head_state` to the dependency graph module.

## Raw Materials

PR #8209

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 12 |
| Contradictions to resolve | 5 |
| Tripwire candidates (score >= 4) | 3 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. **These must be completed FIRST** before any new documentation.

### 1. ObjectiveNode plan field reference

**Location:** `docs/learned/objectives/dependency-graph.md`
**Action:** DELETE_STALE
**Phantom References:** Claims ObjectiveNode has "plan" field (line 28)
**Cleanup Instructions:** Remove all references to the `plan` field from ObjectiveNode field list. The field was removed in commit 3be1ad48e to simplify objective roadmap to single-reference (PR-only) model. Update any field lists to show current state (pr field only).

### 2. RoadmapNode plan field behavior

**Location:** `docs/learned/objectives/roadmap-parser-api.md`
**Action:** DELETE_STALE
**Phantom References:** Describes RoadmapNode plan field behavior (line 83), lists separate plan and pr fields
**Cleanup Instructions:** Remove descriptions of plan field behavior. Update RoadmapNode field documentation to reflect current state with only the pr field. Add note explaining the consolidation rationale.

### 3. RoadmapNode field list

**Location:** `docs/learned/objectives/roadmap-format-versioning.md` (line 24)
**Action:** DELETE_STALE
**Phantom References:** Lists plan field in RoadmapNode definition as one of five fields
**Cleanup Instructions:** Update field list to show four fields only (id, slug, title, pr). Document that the plan field was removed in commit 3be1ad48e as part of consolidation to single-reference model.

### 4. Roadmap table format

**Location:** `docs/learned/objectives/roadmap-format-versioning.md` (line 67)
**Action:** DELETE_STALE
**Phantom References:** Describes 5-column table format with Plan column
**Cleanup Instructions:** Update table format description to show 4-column format (no Plan column). The canonical format is now: ID, Slug, Title, PR.

## Documentation Items

### HIGH Priority

#### 1. Circular import resolution pattern

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session impl-61f3753f

**Draft Content:**

```markdown
### Circular Import with real.py

When importing from `erk_shared.gateway.plan_data_provider.real` in tests fails with circular import, check if the function can be moved to `dependency_graph.py` or another low-dependency module.

**Why this happens**: real.py has deep import dependencies through the chain: real.py -> erk.core.context -> CLI modules -> dash_data.py -> real.py (circular).

**Resolution pattern**:
1. Identify the function causing the import (often a pure-logic function with no I/O)
2. Check if the function's dependencies are available in a lower-level module
3. Move the function to the lower-level module (e.g., dependency_graph.py has no erk.core or CLI dependencies)
4. Update imports in both the original module (which now imports from the lower module) and test files

**Source**: See `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` for `compute_objective_head_state` as an example of this pattern.
```

#### 2. Immediate plan PR field population workflow

**Location:** `docs/learned/objectives/plan-pr-field-workflow.md`
**Action:** CREATE
**Source:** [Impl] Session 9bec9dbd (user correction: "head should contain pr numbers not node headings")

**Draft Content:**

```markdown
# Plan PR Field Workflow

## Overview

When a plan is saved for an objective node, the plan issue number should be stored in the node's `pr` field immediately, not left as null.

## Rationale

Plan issue numbers and PR numbers are identical in erk's Graphite workflow - plan issue #8200 becomes PR #8200 when submitted. Storing the plan number immediately enables:
- Head column display without additional lookups
- Consistent identifier across planning and implementation phases
- No need for separate plan/PR field maintenance

## Implementation

In the plan-save workflow, pass `--pr "#<plan_number>"` instead of `--pr ""` when updating objective nodes to in_progress status.

**File**: See `.claude/commands/erk/plan-save.md` for implementation.

## Anti-pattern

Never pass `--pr ""` for in-progress nodes with active plans. This causes the head column to display "-" instead of the useful plan/PR number.

## Backfill

For existing objectives with null pr fields on in-progress nodes, match open PRs to nodes by branch name patterns (e.g., `plnd/O8197-...`) and update nodes with their corresponding PR numbers.
```

#### 3. compute_objective_head_state() function

**Location:** `docs/learned/objectives/head-state-computation.md`
**Action:** CREATE
**Source:** [Impl] DiffAnalyzer, Session impl-61f3753f

**Draft Content:**

```markdown
# Objective Head State Computation

## Overview

The `compute_objective_head_state` function determines the display string for the head-state column in the objectives dashboard. It centralizes the decision logic that was previously inline in `_build_row_data()`.

## Decision Logic

The function returns a display string based on two inputs: node status and minimum dependency status.

Priority order:
1. **Planning status**: If node status is "planning", return "planning"
2. **In-progress status**: If node status is "in_progress", return "in-progress"
3. **Terminal deps or no deps**: If deps are terminal or absent, return "ready"
4. **Blocked**: Return the blocking dep status with underscores replaced by hyphens

## Source

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` - grep for `def compute_objective_head_state`.

## Test Coverage

The function is tested with 9 parameterized test cases covering all branches. See `tests/unit/gateway/github/metadata/test_dependency_graph.py`.

## Bug Fixed

Before extraction, nodes with `in_progress` status fell through to the "ready" case. Now they explicitly return "in-progress".
```

### MEDIUM Priority

#### 4. GitHub URL construction patterns

**Location:** `docs/learned/reference/github-api-patterns.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 76d18dc8, 9bec9dbd, DiffAnalyzer

**Draft Content:**

```markdown
### GitHub URL Path Patterns

When constructing GitHub URLs programmatically:

| Resource Type | URL Path |
|---------------|----------|
| Issues | `https://github.com/{owner}/{repo}/issues/{number}` |
| Pull Requests | `https://github.com/{owner}/{repo}/pull/{number}` |

**Never use `/issues/` for PRs**, even though GitHub redirects `/issues/N` to `/pull/N` for PRs. Use the semantically correct path.

**Why it matters**:
- Semantic clarity in logs and UI
- Consistent pattern matching in code
- Correct display in link previews
```

#### 5. Test placement by conceptual domain

**Location:** `docs/learned/testing/test-organization.md`
**Action:** CREATE
**Source:** [Impl] Session impl-61f3753f

**Draft Content:**

```markdown
# Test Organization by Conceptual Domain

## Pattern

When testing extracted functions, place tests based on conceptual domain rather than usage location.

## Example

`compute_objective_head_state` is used in `real.py` but tests go in `test_dependency_graph.py` because:
- The function depends on dependency graph concepts (`min_dep_status`, `_TERMINAL_STATUSES`)
- Placing tests with usage location would create import issues (real.py has deep dependencies)
- Conceptual grouping creates clearer test organization

## Guideline

**Ask**: "What domain concepts does this function operate on?"

**Place tests** in the test file for that domain, not in the test file for where the function is called.

## Benefits

- Avoids circular imports during test execution
- Groups related behavior together
- Makes test files more cohesive
```

#### 6. Reset-then-apply pattern for mixed branches

**Location:** `docs/learned/planning/pr-operations.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 452da764, 5ce49579

**Draft Content:**

```markdown
### Reset-then-Apply for Mixed Branches

When a branch contains both wanted and unwanted changes bundled together, use hard-reset and selective re-application rather than cherry-pick or revert.

**Pattern**:
1. Analyze the diff: `git diff master...HEAD --stat` to see all affected files
2. Categorize changes: Separate wanted (bug fixes) from unwanted (feature additions)
3. Hard reset: `git reset --hard master`
4. Selectively apply: Edit files to re-add only desired changes
5. Verify: `git diff --stat` to confirm only wanted changes remain

**When to use**: When unwanted changes are pervasive (many files) but wanted changes are confined (few files), extraction is easier than attempted surgery.

**Example**: Branch had plan field additions touching 9 files but bug fixes only in 3 files. Reset and re-apply the 3-file changes was cleaner than reverting the 9-file feature.
```

#### 7. Edit tool requires Read in current session

**Location:** `docs/learned/capabilities/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 452da764 (Edit tool errors)

**Draft Content:**

```markdown
### Edit Tool Requires Read in Current Session

Always use the Read tool before editing a file, even if you've read the file previously via grep or git show.

**Trigger**: Before editing any file in Claude Code

**Why**: The Edit tool tracks which files have been Read in the current session. Reading via grep, git show, or from previous sessions doesn't count.

**Error message**: "file has not been read yet" or "file modified since read"

**Pattern**:
```
1. Read(file_path="/path/to/file.py")
2. Edit(file_path="/path/to/file.py", old_string="...", new_string="...")
```

**After git reset**: Even if you just read a file, `git reset --hard` invalidates the read state. Read files again before editing.
```

### LOW Priority

#### 8. Test extraction pattern for complex logic

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session 452da764

**Draft Content:**

```markdown
### Test Extraction for Complex Logic

When reviewers request tests for embedded conditional logic (if/elif chains), extract the logic into a standalone function rather than testing through complex mocks.

**Pattern**:
1. Identify the conditional logic to test
2. Extract into a pure function with clear inputs and outputs
3. Write parametrized tests for all branches
4. Replace inline logic with function call

**Benefits**:
- Direct unit testing without heavyweight provider mocks
- Clearer test cases mapping to branches
- Reusable logic if needed elsewhere
```

#### 9. Schema migration field reference checking

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 76d18dc8, 9bec9dbd

**Draft Content:**

```markdown
### Schema Migration Field Cleanup

**Trigger**: After removing fields from dataclasses or schemas

**Action**: Grep test fixtures for removed field names to catch stale references.

**Example**: plan -> pr field migration left test YAML with stale `plan:` references that were silently ignored.

**Command**: `grep -r "plan:" tests/ --include="*.yaml" --include="*.yml"`

**What to check**:
- Test fixture YAML/JSON files
- Fake implementation data
- Docstrings referencing old fields
- Test assertions checking old field values
```

#### 10. Stale test parameters after signature changes

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 9bec9dbd

**Draft Content:**

```markdown
### Stale Test Parameters After Refactoring

**Trigger**: After removing parameters from method signatures

**Action**: Grep test files for old parameter name to find stale call sites.

**Why it matters**: Tests may pass kwargs that the production code no longer accepts, causing TypeError at runtime.

**Example**: `learn_issue_states` parameter removed from `_build_row_data()` but 10+ test call sites still passed it. Error: `TypeError: got an unexpected keyword argument 'learn_issue_states'`

**Command**: `grep -r "learn_issue_states" tests/`
```

#### 11. Format check after Edit operations

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session impl-61f3753f

**Draft Content:**

```markdown
### Format Check After Edit Operations

**Trigger**: After making multiple Edit tool calls

**Action**: Run `ruff format` before running the full test suite.

**Why**: Multiple Edit calls can result in unformatted code that passes local execution but fails CI format checks.

**Pattern**:
1. Make Edit calls for implementation
2. Run `uv run ruff format <file>` on modified files
3. Then run pytest or make fast-ci
```

## Contradiction Resolutions

All 5 detected contradictions are actually DELETE_STALE cases rather than true contradictions. See the "Stale Documentation Cleanup" section above for resolution details.

The contradictions arose because the `plan` field was deliberately removed from RoadmapNode/ObjectiveNode in commit 3be1ad48e (Feb 25, 2026) to "Simplify objective roadmap to single-reference (PR-only) model", but documentation was not updated.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Circular Import When Testing real.py

**What happened:** Test file imported `compute_objective_head_state` from `real.py`, triggering a circular import chain through erk.core.context -> CLI -> dash_data.py -> real.py.

**Root cause:** real.py has deep import dependencies that create import cycles when accessed from test context.

**Prevention:** Before extracting functions from high-level modules, check import depth. Prefer extracting to low-level modules (dependency_graph.py) over high-level ones (real.py).

**Recommendation:** TRIPWIRE - This pattern is non-obvious, cross-cutting, and has high destructive potential (blocks test execution entirely).

### 2. Schema Migration Leaves Test Fixtures Stale

**What happened:** Test YAML referenced `plan: '#100'` field that was removed in schema migration, but tests passed because they never exercised the code path surfacing the discrepancy.

**Root cause:** Field removed from production code but tests not updated simultaneously.

**Prevention:** After schema migrations, grep test fixtures for removed field names.

**Recommendation:** TRIPWIRE - Silent data loss, tests passing but feature broken in production.

### 3. Edit Without Read in Current Session

**What happened:** Multiple "file has not been read yet" errors when attempting to edit files after git reset.

**Root cause:** Edit tool requires Read in same session; git operations and grep don't count.

**Prevention:** Always call Read before Edit, even if contents known from other tools.

**Recommendation:** TRIPWIRE - Non-obvious external tool quirk.

### 4. Format Check Fails After Implementation

**What happened:** Multiple Edit tool calls left code unformatted, causing CI failure.

**Root cause:** Edit tool doesn't auto-format; multiple edits compound the problem.

**Prevention:** Run ruff format immediately after Edit operations.

**Recommendation:** ADD_TO_DOC - Standard practice, not tripwire-worthy.

### 5. Wrong URL Path for GitHub Resources

**What happened:** Code generated `/issues/{num}` URLs when linking to PRs.

**Root cause:** Confusion between issue and PR URL patterns.

**Prevention:** Document standard URL patterns; use semantic paths.

**Recommendation:** ADD_TO_DOC - Low severity, GitHub redirects anyway.

### 6. Stale Test Parameters After Signature Changes

**What happened:** 10+ test call sites passed `learn_issue_states` parameter that no longer existed.

**Root cause:** Method signature refactored but test call sites not updated.

**Prevention:** Grep test directory for old parameter name after signature changes.

**Recommendation:** ADD_TO_DOC - Standard refactoring concern.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Circular Import with real.py

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive +2)
**Trigger:** Before importing from `erk_shared.gateway.plan_data_provider.real` in tests
**Warning:** "real.py has deep import dependencies (erk.core.context -> CLI -> dash_data.py -> real.py). If circular import occurs, move function to lower-level module like dependency_graph.py"
**Target doc:** `docs/learned/architecture/tripwires.md`

This is the highest-priority tripwire because it completely blocks test execution and requires code restructuring to resolve. The circular import chain is non-obvious and involves multiple modules. Future agents attempting to test code in real.py will encounter this issue.

### 2. Edit Tool Requires Read in Session

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before editing files in Claude Code
**Warning:** "Always use Read tool first in current session, even if you've read the file via grep/git show. Edit tool requires Read to be called in same session."
**Target doc:** `docs/learned/capabilities/tripwires.md`

This tripwire addresses a Claude Code-specific behavior that repeatedly caused workflow interruptions. The requirement isn't documented in the tool description and catches agents by surprise.

### 3. Schema Migration Field Cleanup

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** After removing fields from dataclasses/schemas
**Warning:** "Grep test files for removed field name. Update test fixtures, fakes, and docstrings. Example: plan -> pr migration left test YAML with stale plan: references"
**Target doc:** `docs/learned/testing/tripwires.md`

Schema migrations create silent failures where tests pass but production behavior is wrong. The plan field removal demonstrated this - tests referenced the old field name and data was silently lost during parsing.

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Format Check After Edit Operations

**Score:** 3/10 (Repeated pattern +1, Cross-cutting +2)
**Notes:** Only becomes an issue when making multiple edits. Could potentially be automated in hooks. Current behavior is "run ruff format manually after edits." If more sessions encounter this, consider promotion to full tripwire.

### 2. Stale Test Parameters After Refactoring

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Standard refactoring concern, but the scale (10+ occurrences) in this session suggests it's worth documenting. The error message (TypeError: unexpected keyword argument) is clear, so manual detection is possible. May warrant promotion if agents repeatedly miss this step.
