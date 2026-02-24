# Documentation Plan: Fix objective update after landing for plnd/ branches

## Context

This plan addresses documentation needs arising from PR #8086, which fixed a bug where objective updates would fail after landing PRs from `plnd/` branches. The core issue was a timing problem: the `erk land` command's execution pipeline deleted the branch before attempting to look up plan and objective context, causing branch-based discovery to fail.

The fix establishes a critical architectural pattern for erk: **capture context before operations that may destroy the context source**. The implementation introduced a `--plan` direct lookup option that threads through 5+ files in the land execution pipeline, allowing objective updates to succeed even after branch deletion. This pattern has cross-cutting applicability to any multi-step operation where early steps may delete resources needed by later steps.

The implementation session was exemplary (zero errors, methodical execution, comprehensive test coverage), making this an ideal source for learned documentation. The patterns discovered here will prevent future developers from repeating the same timing mistakes.

## Summary

| Metric                        | Count |
| ----------------------------- | ----- |
| Documentation items           | 6     |
| Contradictions to resolve     | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Context capture before pipeline execution

**Location:** `docs/learned/planning/objective-update-after-land.md`
**Action:** UPDATE
**Source:** [Plan], [Impl], [PR #8086]

**Draft Content:**

```markdown
## Critical Timing Constraint: Context Capture Before Pipeline

When implementing operations that merge PRs and delete branches, all required context must be captured BEFORE the execution pipeline runs.

### The Problem

The `run_execution_pipeline()` function performs merge and cleanup operations that delete branches. Any branch-based discovery after this point will fail:

- `get_plan_for_branch()` requires the branch to exist (or PR to retain head ref)
- `get_objective_for_branch()` relies on plan discovery
- `PlannedPRBackend` uses GitHub API calls that may fail after branch deletion

### The Solution

Capture `plan_id` and `objective_number` BEFORE calling execution pipeline:

See `_execute_land_directly()` in `src/erk/cli/commands/land_cmd.py` (grep for "Capture plan context BEFORE execution pipeline")

The captured values are then passed through the update chain, bypassing the need for branch-based discovery.

### Two Capture Locations

Both execution modes must capture context early:

1. **Direct execution** (`_execute_land_directly`): Captures before `run_execution_pipeline()`
2. **Navigation mode** (`_land_target`): Captures before `render_land_execution_script()`

See PR #8086 for the complete implementation.
```

---

#### 2. Direct lookup with fallback pattern

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8086]

**Draft Content:**

```markdown
## Direct Lookup with Fallback Resilience

**Trigger:** Before implementing operations that may run after deletion of discovery source

**Pattern:** Provide direct lookup option as primary path, with discovery as fallback.

When a script or operation needs to look up context (plan, objective, etc.) but may run after the discovery source (branch, file, metadata) has been deleted:

1. Accept an optional direct parameter (e.g., `--plan <number>`)
2. When provided, use direct lookup (no discovery needed)
3. When not provided, fall back to discovery-based lookup (backward compatibility)

### Implementation Structure

See direct lookup logic in `objective_apply_landed_update()` in `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py` (grep for "Resolve plan")

### Advantages

- Better than retrying failed lookups (wastes time, may still fail)
- Better than arbitrary delays (unreliable, poor UX)
- Better than error messages (forces user intervention)
- No breaking changes (existing calls without direct option still work)

See PR #8086 for complete implementation.
```

---

#### 3. Parameter threading through execution pipeline

**Location:** `docs/learned/planning/objective-update-after-land.md`
**Action:** UPDATE
**Source:** [Plan], [Impl], [PR #8086]

**Draft Content:**

```markdown
## Parameter Threading Chain

When adding new context to the land execution pipeline, the parameter must be threaded through multiple files:

### The 5-Step Chain

1. **Capture**: `_execute_land_directly()` or `_land_target()` - Capture value before pipeline
2. **Render**: `render_land_execution_script(plan_number=...)` - Add to function signature
3. **Execute**: `land_execute --plan-number X` - Add CLI option
4. **Update**: `objective_update_after_land --plan-number X` - Pass through to command
5. **Apply**: `objective_apply_landed_update --plan X` - Use for direct lookup

### Conditional Inclusion Pattern

For optional parameters in generated scripts:

See `render_land_execution_script()` in `src/erk/cli/commands/land_cmd.py` for the conditional flag pattern.

### Test Update Requirements

When adding keyword-only parameters to widely-used functions:
- All test call sites must be updated (even when passing `None`)
- Use `replace_all=True` for bulk updates in test files
- Test both positive (value provided) and negative (None) cases

See PR #8086 for complete threading example.
```

---

### MEDIUM Priority

#### 4. PlannedPRBackend discovery timing

**Location:** `docs/learned/planning/planned-pr-backend.md`
**Action:** UPDATE
**Source:** [Plan], [PR #8086]

**Draft Content:**

```markdown
## Discovery Timing Constraints

### API Dependency

`resolve_plan_id_for_branch()` uses GitHub API call (`get_pr_for_branch()`) to resolve plan ID. This requires either:

- Branch still exists remotely, OR
- PR retains head ref metadata after merge

### Timing Risk

If called after branch deletion (e.g., after `run_execution_pipeline()`), the API call may fail because:
- Branch no longer exists on remote
- GitHub may not retain head ref metadata for merged PRs

### Mitigation Strategies

1. **Capture before deletion**: Resolve plan_id before execution pipeline runs
2. **Use direct lookup**: Pass `--plan` parameter to bypass branch-based discovery

### Contrast with GitHubPlanStore

`GitHubPlanStore` uses zero-cost regex on branch name (no API dependency):
- Branch pattern: `P<number>-` or `<number>-`
- Resolution: Immediate string parsing
- Deletion impact: None (pattern embedded in name)

`PlannedPRBackend` depends on API:
- Branch pattern: `plnd/O<number>-`
- Resolution: API call to find PR for branch
- Deletion impact: May fail if called after deletion

See `resolve_plan_id_for_branch()` in `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`.
```

---

#### 5. Dual execution modes consistency

**Location:** `docs/learned/planning/dual-execution-modes.md`
**Action:** CREATE
**Source:** [Plan], [Impl], [PR #8086]

**Draft Content:**

```markdown
---
title: Dual Execution Modes in Land Command
read-when: modifying land command execution flow, working on navigation vs direct execution
---

# Dual Execution Modes in Land Command

The `erk land` command has two execution modes that must handle edge cases identically.

## Navigation Mode (`_land_target`)

Generates a shell script for the user to source. Allows directory navigation after landing.

- Captures context before script generation
- Script calls `erk exec land-execute` with captured parameters
- User sources the script to execute

## Direct Execution Mode (`_execute_land_directly`)

Runs the merge immediately. Stays in current directory.

- Must capture context before `run_execution_pipeline()`
- Executes pipeline synchronously
- Runs objective update in same process

## Consistency Requirement

Both modes MUST handle edge cases identically:

1. **Context capture timing**: Both capture plan_id/objective_number BEFORE execution
2. **Parameter threading**: Both pass captured values to objective update
3. **Fail-open behavior**: Both treat objective update as non-blocking

## Why the Bug Only Affected Direct Mode

In PR #8086, the bug only affected direct execution because:
- Navigation mode happened to capture context early (for script generation)
- Direct mode captured context AFTER execution pipeline (branch deleted)

This was accidental consistency, not by design. The fix made both modes explicitly consistent.

## Recommendation

Consider extracting shared context capture logic to ensure consistency. When modifying either mode, always check both.

See `_execute_land_directly()` and `_land_target()` in `src/erk/cli/commands/land_cmd.py`.
```

---

### LOW Priority

#### 6. Test pattern for direct lookup with fallback

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8086]

**Draft Content:**

```markdown
## Testing Direct Lookup with Fallback

**Trigger:** Adding direct lookup option with fallback to discovery

When implementing the direct lookup pattern (see architecture/tripwires.md), test three paths:

### Test Cases Required

1. **Direct lookup succeeds**: Pass `--plan` flag, verify correct resolution without branch discovery
2. **Direct lookup fails**: Pass invalid `--plan`, verify clear error message
3. **Fallback works**: Omit `--plan`, verify branch-based discovery succeeds

### Key Assertion

Verify fallback is NOT used when direct option is provided. The direct path should short-circuit discovery.

### Example Pattern

See `test_plan_direct_lookup_skips_branch_discovery()` and `test_plan_direct_lookup_not_found()` in `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`.
```

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced files in existing docs were verified to exist.

## Prevention Insights

Errors and failed approaches discovered during the ORIGINAL buggy implementation (planning session):

### 1. Branch deleted before context lookup

**What happened:** `erk land` tried to discover plan/objective from branch after execution pipeline had already deleted it.
**Root cause:** Timing issue - discovery happened after branch deletion, not before.
**Prevention:** Capture all required context (plan_id, objective_number) BEFORE execution pipeline runs.
**Recommendation:** TRIPWIRE (implemented in this plan)

### 2. Plan identifier mismatch for plnd/ branches

**What happened:** Branch naming `plnd/O8036-*` encodes objective number (8036), but node's `plan` field was PR number (#8070). Auto-matching failed.
**Root cause:** `extract_leading_issue_number()` extracts objective number from branch, not plan/PR number.
**Prevention:** Add plan identifier to branch name OR lookup PR number from branch via GitHub API before matching.
**Recommendation:** ADD_TO_DOC (documented in planned-pr-backend.md)

### 3. Empty matched_steps forced manual fallback

**What happened:** When auto-matching failed, agent improvised with unsafe `gh issue edit` commands.
**Root cause:** No built-in recovery when auto-matching fails; exec script returns empty list silently.
**Prevention:** Exec script should suggest alternative strategies (PR metadata lookup, user-specified node) instead of silent empty return.
**Recommendation:** CONTEXT_ONLY (agent behavior issue, not recurring pattern)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Context capture before pipeline execution

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before running execution pipeline that deletes branches
**Warning:** Capture plan_id and objective_number BEFORE pipeline runs. Branches may be deleted during merge/cleanup, making discovery-based lookup fail. In `land_cmd.py`, capture context before calling `run_execution_pipeline()`. See PR #8086.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is critical because the failure mode is silent - the objective update simply doesn't happen, leaving roadmap nodes stale. The bug only surfaces during post-land review when users notice missing updates.

### 2. Direct lookup with fallback resilience pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding discovery-based lookup to an exec script or operation that may run after deletion of discovery source
**Warning:** Provide direct lookup option as primary path (e.g., `--plan <number>`), with discovery as fallback. Discovery may fail if the source (branch, file, metadata) is deleted before the operation runs. Pattern: check direct option first, fall back to discovery if not provided. See `objective_apply_landed_update.py` in PR #8086.
**Target doc:** `docs/learned/architecture/tripwires.md`

This pattern applies beyond planning - any exec script that depends on branch-based discovery should consider this pattern.

### 3. Parameter threading through land pipeline

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +1, Non-obvious +1)
**Trigger:** Before adding a new parameter to land execution pipeline
**Warning:** Thread parameter through 5+ places: (1) capture point before pipeline, (2) render_land_execution_script signature, (3) script generation with conditional inclusion, (4) land_execute CLI options, (5) downstream exec scripts. Update all test invocations. See PR #8086 for complete threading example.
**Target doc:** `docs/learned/planning/tripwires.md`

Missing any step silently breaks the chain. The parameter appears to be passed but never arrives at the final destination. Tests caught this in PR #8086 because all test files needed signature updates.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Two-mode execution consistency

**Score:** 3/10 (Cross-cutting +2, Non-obvious +1)
**Notes:** Both navigation mode (`_land_target`) and direct mode (`_execute_land_directly`) must handle edge cases identically. Not tripwire-worthy yet because this is the first instance of the pattern causing a bug. If similar divergence causes future issues, promote to tripwire.

### 2. Test pattern for direct lookup

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** When adding direct lookup with fallback, test three paths (direct succeeds, direct fails, fallback works). Not tripwire-worthy if documented in testing patterns; added to testing/tripwires.md as documentation item.

## Key Architectural Insights

### Temporal Dependencies Pattern

Operations that delete resources needed for subsequent lookups create timing dependencies. The fix establishes this pattern:

- **Before (buggy):** Context lookup -> Execute -> Update (lookup fails)
- **After (fixed):** Context capture -> Execute -> Update (with captured context)

This pattern applies to:
- Branch deletion workflows (this PR)
- Worktree cleanup operations
- Any operation with "execute then update" structure

### Fail-Open Design Pattern

The objective update is designed fail-open: if the update fails, the land operation still succeeds. This is correct because:
1. PR merge is the primary operation (already succeeded)
2. Objective update is metadata reconciliation (nice-to-have)
3. User can retry manually if needed
4. Blocking land on objective update would be worse UX

This pattern is already documented in `docs/learned/architecture/fail-open-patterns.md`.

## Implementation Notes

**Session quality:** EXCELLENT
- Zero implementation errors in impl sessions
- Methodical execution following plan exactly
- Clean test-driven development
- All 197+ tests passing
- No user corrections needed

**Documentation value:** HIGH
- 3 tripwire-worthy patterns discovered
- 5 existing docs require updates
- 1 new doc needed (dual-execution-modes.md)
- Clear prevention insights for future work
- Strong architectural lessons applicable beyond planning domain
