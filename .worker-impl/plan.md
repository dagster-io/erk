# Plan: Consolidated Documentation from 6 Learn Plans

> **Consolidates:** #6378, #6374, #6372, #6360, #6357, #6355

## Source Plans

| #    | Title                                                                      | Items Merged | Status |
| ---- | -------------------------------------------------------------------------- | ------------ | ------ |
| 6378 | Update discriminated union docs with "does the caller continue?" framing   | 0 items      | ALL IMPLEMENTED (PR #6376 merged) |
| 6374 | Skip autofix on plan-review PRs (including push events)                    | 3 items      | Mostly not implemented |
| 6372 | Add /erk:plan-review to plan-save next steps output                        | 2 items      | Mostly not implemented |
| 6360 | Remove Docker and Codespace isolation modes from implement/prepare         | 4 items      | Mostly not implemented |
| 6357 | Phase 4: Git Branch/Worktree Creation Failures to Discriminated Unions     | 5 items      | Mostly not implemented |
| 6355 | Learn Plan: Issue #6335 - UserFacingCliError Implementation                | 1 item       | Partially implemented |

## What Changed Since Original Plans

- PR #6376 merged: "does the caller continue?" framing fully implemented (#6378 complete)
- PR #6375 merged: Worktree add/remove converted BACK from discriminated unions to exceptions
- PR #6371 merged: Step-level label queries for push events in CI
- PR #6359 merged: Docker/Codespace flags removed from implement/prepare
- PR #6353 merged: UserFacingCliError introduced and RuntimeError replaced in 8 files
- PR #6348 merged: create_branch and add_worktree converted to discriminated unions

## Investigation Findings

### Corrections to Original Plans

- **#6378**: All items already implemented. No remaining work.
- **#6357 Item 8**: Plan references `docs/learned/testing/fake-driven-testing.md` for UPDATE, but this file doesn't exist. The content would need to go into `docs/learned/testing/testing.md` instead.
- **#6372 Item 5**: `docs/learned/sessions/learn-session-discovery.md` doesn't exist, but the content IS covered by existing `docs/learned/sessions/discovery-fallback.md`. No new file needed.
- **#6357 Items 10-12**: Learn command pipeline, workflow constraints, and preprocessing constraints are tangential to the Phase 4 gateway work. These describe the learn workflow itself, not the gateway patterns learned. Drop as low-value.

### Overlap Analysis

- **Discriminated union patterns** appear in #6378 (done), #6357 (gateway examples), and #6355 (CLI consumer pattern). The discriminated-union-error-handling.md updates from #6378 and #6355 are complete. Only #6357's branch creation examples are missing.
- **Error handling patterns** appear in #6357 (gateway error boundaries) and #6355 (UserFacingCliError anti-patterns). These are complementary, not overlapping.
- **CI patterns** from #6374 are self-contained with no overlap with other plans.
- **Feature removal docs** from #6360 are self-contained cleanup items.

## Remaining Gaps (Prioritized)

### HIGH Priority - Stale/Incorrect Documentation

These items fix documentation that is actively misleading:

1. **Remove obsolete --codespace glossary entry** (`docs/learned/glossary.md:836-850`)
2. **Remove obsolete "Remote agent" row** from plan-implement.md (`docs/learned/cli/plan-implement.md:91-97`)

### HIGH Priority - Missing Patterns Worth Documenting

3. **CREATE `docs/learned/ci/github-actions-label-queries.md`** - Step-level label query pattern for push events _(from #6374)_
4. **CREATE `docs/learned/architecture/gateway-error-boundaries.md`** - Error boundary responsibilities: try/except only in real.py _(from #6357)_
5. **CREATE `docs/learned/architecture/git-operation-patterns.md`** - LBYL git operation pattern with `git show-ref --verify` _(from #6357)_

### MEDIUM Priority - Tripwire Updates

6. **UPDATE `docs/learned/ci/workflow-gating-patterns.md`** - Add step-level API query section after "Autofix Safety Pattern" _(from #6374)_
7. **UPDATE `docs/learned/ci/tripwires.md`** - Add push event label check asymmetry tripwire (score 6/10) _(from #6374)_
8. **UPDATE `docs/learned/architecture/gateway-abc-implementation.md`** - Add branch/worktree concrete examples to 5-file checklist _(from #6357)_

### MEDIUM Priority - Missing Documentation

9. **CREATE `docs/learned/ci/makefile-prettier-ignore-path.md`** - Prettier uses `--ignore-path .gitignore`, not `.prettierignore` _(from #6360)_
10. **CREATE `docs/learned/cli/error-handling-antipatterns.md`** - RuntimeError anti-pattern documentation _(from #6355)_

### LOW Priority - Nice to Have

11. **UPDATE `docs/learned/architecture/gateway-inventory.md`** - Clarify codespace gateway persistence post-removal _(from #6360)_
12. **UPDATE `docs/learned/architecture/discriminated-union-error-handling.md`** - Add create_branch concrete example _(from #6357)_
13. **UPDATE `docs/learned/architecture/branch-manager-abstraction.md`** - Note discriminated union delegation _(from #6357)_
14. **UPDATE `docs/learned/testing/testing.md`** - Add fake error simulation section _(from #6357)_
15. **CREATE `docs/learned/planning/plan-metadata-fields.md`** - branch_name requirement for PR lookup _(from #6372)_

## Implementation Steps

### Step 1: Fix stale documentation (HIGH) _(from #6360)_

**File:** `docs/learned/glossary.md`
- Delete lines 836-850 (the entire `### --codespace` section)
- Verification: grep for `--codespace` in glossary.md returns no results

**File:** `docs/learned/cli/plan-implement.md`
- Remove the "Remote agent" row from the table at lines 91-97
- Update any surrounding text that references remote execution modes
- Verification: No mention of "Remote agent" or `--codespace` in plan-implement.md

### Step 2: Create CI label query documentation (HIGH) _(from #6374)_

**File:** `docs/learned/ci/github-actions-label-queries.md`
- Document the step-level GitHub API label query pattern
- Include the `gh api repos/.../pulls/<PR> --jq` pattern from `.github/workflows/ci.yml` lines 193-205
- Cover: Problem statement (push event asymmetry), solution (step-level API query), skip condition consolidation
- Add frontmatter with tripwire for push event label checks
- Verification: File exists with read_when and tripwire frontmatter

### Step 3: Create gateway error boundaries doc (HIGH) _(from #6357)_

**File:** `docs/learned/architecture/gateway-error-boundaries.md`
- Document where try/except belongs in the 5-implementation gateway pattern:
  - `real.py`: Catches subprocess errors, converts to discriminated union
  - `fake.py`: Returns error discriminant based on constructor params (NO try/except)
  - `dry_run.py`: Returns success discriminant (NO try/except)
  - `printing.py`: Logs then delegates (NO try/except)
- Add frontmatter with tripwire
- Verification: File exists with clear examples for each implementation type

### Step 4: Create LBYL git operation patterns doc (HIGH) _(from #6357)_

**File:** `docs/learned/architecture/git-operation-patterns.md`
- Document `git show-ref --verify refs/heads/{name}` LBYL pattern
- Contrast with fragile exception message parsing
- Show when try/except IS appropriate (multiple failure modes, atomic operations)
- Add frontmatter with tripwire about CalledProcessError parsing
- Verification: File exists with concrete git command examples

### Step 5: Update CI workflow-gating-patterns and tripwires (MEDIUM) _(from #6374)_

**File:** `docs/learned/ci/workflow-gating-patterns.md`
- Add new section "Step-Level Label Query Pattern" after the existing "Autofix Safety Pattern" section
- Document the defense-in-depth approach: job-level condition + step-level API query
- Show skip condition consolidation pattern ("Determine if autofix should run" step)

**File:** `docs/learned/ci/tripwires.md`
- The tripwire for push event label check asymmetry should be auto-generated from the frontmatter in `github-actions-label-queries.md`
- Run `erk docs sync` to regenerate tripwires

### Step 6: Update gateway-abc-implementation.md (MEDIUM) _(from #6357)_

**File:** `docs/learned/architecture/gateway-abc-implementation.md`
- Enhance the "Return Type Changes" section (lines 88-107) with branch/worktree concrete examples
- Add Phase 4 (PR #6348) as a canonical example alongside the existing PR #6294 example
- Verification: Section references both merge_pr and create_branch/add_worktree migrations

### Step 7: Create Prettier ignore path doc (MEDIUM) _(from #6360)_

**File:** `docs/learned/ci/makefile-prettier-ignore-path.md`
- Document that Makefile uses `--ignore-path .gitignore` for Prettier
- Add frontmatter with tripwire for `.prettierignore` modifications
- Verification: File exists with clear warning

### Step 8: Create RuntimeError anti-pattern doc (MEDIUM) _(from #6355)_

**File:** `docs/learned/cli/error-handling-antipatterns.md`
- Document why RuntimeError is wrong for expected CLI failures
- Show migration path: RuntimeError -> UserFacingCliError
- Reference the 47 files still containing RuntimeError
- Add frontmatter with tripwire
- Verification: File exists with migration examples

### Step 9: Low-priority updates _(from #6360, #6357, #6372)_

**File:** `docs/learned/architecture/gateway-inventory.md`
- Add clarification note to Codespace/CodespaceRegistry sections that these persist for `erk codespace` commands despite removal from implement/prepare

**File:** `docs/learned/architecture/discriminated-union-error-handling.md`
- Add create_branch example near existing worktree example (around line 82)

**File:** `docs/learned/architecture/branch-manager-abstraction.md`
- Add note about discriminated union delegation in create_branch

**File:** `docs/learned/testing/testing.md`
- Add section on fake error simulation with `FakeGitBranchOps(create_branch_error=...)` pattern

**File:** `docs/learned/planning/plan-metadata-fields.md`
- Document branch_name requirement for `get-pr-for-plan` and learn workflows

### Step 10: Regenerate indexes

- Run `erk docs sync` to regenerate tripwires-index.md, category tripwires, and index.md

## Attribution

Items by source:
- **#6378**: No remaining items (all implemented)
- **#6374**: Steps 2, 5
- **#6372**: Step 9 (plan-metadata-fields.md only)
- **#6360**: Steps 1, 7, 9 (gateway-inventory, glossary, plan-implement)
- **#6357**: Steps 3, 4, 6, 9 (discriminated-union examples, branch-manager, testing)
- **#6355**: Step 8

## Verification

After implementation:
1. Run `erk docs sync` to regenerate all auto-generated files
2. Verify no references to removed `--docker`/`--codespace` flags in docs/learned/
3. Verify new files have proper frontmatter with `read_when` and `tripwires` sections
4. Run `make fast-ci` to ensure no formatting/lint issues