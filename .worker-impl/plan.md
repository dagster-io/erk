# Documentation Plan: Fix: Table plan column not cleared when PR is set + enforce # prefix

## Context

This PR (#7151) fixed two related bugs in objective roadmap management that stemmed from a fundamental architectural challenge: maintaining consistency across three data stores (YAML frontmatter, body markdown table, and comment markdown table) that all represent the same logical roadmap data. The first bug caused plan values to persist in markdown tables even when they should have been auto-cleared after a PR was set, creating divergence between the frontmatter (which correctly showed `plan: null`) and the tables (which preserved the stale plan reference). The second bug allowed plan/PR references to be written without the required `#` prefix, bypassing validation because existing checks used guard clauses that silently skipped non-conforming values rather than flagging them as invalid.

Future agents working on roadmap data need to understand this dual-write consistency pattern. When a single logical operation (like setting a PR reference) touches multiple representations of the same data, all update paths must implement identical semantics. The auto-clear logic existed in the frontmatter updater but was missing from both table updaters. This is the second instance of frontmatter/table divergence in the codebase, suggesting it should be documented as a cross-cutting architectural concern with explicit audit requirements.

The implementation also revealed important knowledge about the v2 objective format: the body contains only YAML frontmatter while markdown tables live in a separate comment body. Test assertions that target the wrong location will fail in confusing ways. Additionally, the session demonstrated best practices for handling branch divergence after PR submission and proper Graphite cache management after raw git operations.

## Raw Materials

https://gist.github.com/schrockn/0084f3f8deb9633651d6a525992d5795

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 15    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Dual-Write Consistency Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Plan], [Impl], [PR #7151]

**Draft Content:**

```markdown
## Dual-Write Consistency Pattern

- action: "implementing functions that update roadmap data in frontmatter, body table, or comment table"
  warning: "Audit ALL write paths for semantic consistency. Auto-clear/auto-infer/auto-compute logic must be replicated across all locations. The frontmatter and table updaters must implement identical semantics for operations like auto-clearing plan when PR is set."

When multiple update functions modify the same logical data (e.g., roadmap steps stored in YAML frontmatter, body table, and comment table), all functions must implement identical auto-clear, auto-infer, and auto-compute semantics.

### The Problem

A single logical operation (e.g., "set PR reference for step 1.2") may touch multiple data stores:
- YAML frontmatter in issue body
- Markdown table in issue body (v1 format)
- Markdown table in comment body (v2 format)

If one updater implements auto-clear logic (e.g., "clear plan when PR is set") but others preserve existing values, the stores diverge.

### Audit Checklist

Before merging any PR that modifies roadmap update logic:
1. Identify all functions that write to the same logical data
2. Verify each function handles the same edge cases identically
3. Write integration tests that verify all stores produce identical output for the same operation

### Source

See `update_step_in_frontmatter()` in `erk_shared/gateway/github/metadata/roadmap.py` and `_replace_table_in_text()` / `_replace_step_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` for the canonical implementation of auto-clear semantics.
```

---

#### 2. Graphite Cache Invalidation Tripwire

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Graphite Cache After Raw Git Operations

- action: "running git rebase, git cherry-pick, or git reset"
  warning: "Always run `gt track --no-interactive` immediately after raw git operations that change commit SHAs. Without this, `gt restack` will fail with 'diverged from tracking' errors because Graphite's cache (.graphite_cache_persist) still references old SHAs."

### Why This Matters

Graphite maintains its own cache of commit SHAs to track stack relationships. When you run raw git operations that rewrite history (rebase, cherry-pick, reset), the actual commits change but Graphite's cache doesn't update automatically.

### The Fix

After any raw git operation that changes commit SHAs:
```bash
git rebase origin/branch-name  # Changes commit SHAs
gt track --no-interactive      # MUST run to update Graphite cache
gt restack --no-interactive    # Now safe to restack
```

### Source

This pattern was discovered during sync-divergence resolution. See the `sync-divergence` skill for the complete workflow.
```

---

#### 3. Check 9 Validation Documentation

**Location:** `docs/learned/objectives/roadmap-validation.md`
**Action:** UPDATE
**Source:** [PR #7151]

**Draft Content:**

```markdown
## Reference Format Validation

### Check 9: Plan/PR References Must Use `#` Prefix

All plan and PR references in the roadmap table must use the `#` prefix format (e.g., `#7146` not `7146`).

**Why this check exists:**
1. **GitHub auto-linking**: GitHub markdown automatically converts `#7146` to clickable issue links
2. **Data integrity**: Unprefixed numbers can be silently skipped by validation checks that use guard clauses like `if step.plan.startswith("#")`
3. **Consistency**: All references follow the same format

**Validation behavior:**
- Scans all roadmap steps for plan/PR values
- Fails if any reference lacks the `#` prefix
- Reports the first invalid reference found (fail-fast pattern)

**Migration path:**
If you have objectives with unprefixed references:
1. Run `erk objective check --allow-legacy` to bypass the check temporarily
2. Use `erk exec update-roadmap-step` with proper `#` prefixes to fix each reference
3. Run `erk objective check` again to verify

Add to the Semantic vs Structural Decision Table:

| Question | Type | Rationale |
|----------|------|-----------|
| Are plan/PR references prefixed with #? | Semantic | Prevents invalid refs that don't auto-link in GitHub markdown |

### Source

See `validate_objective()` in `src/erk/cli/commands/objective/check_cmd.py`, Check 9 implementation (grep for "Plan/PR references use '#' prefix").
```

---

#### 4. Three-Store V2 Format Structure

**Location:** `docs/learned/objectives/v2-format-structure.md`
**Action:** CREATE
**Source:** [Impl], [PR #7151]

**Draft Content:**

```markdown
---
title: V2 Objective Format Structure
read-when:
  - writing tests for v2 objectives
  - implementing updates to v2 objective data
  - debugging v2 format divergence issues
---

# V2 Objective Format Structure

V2 objectives store roadmap data in **three distinct locations**, all of which must be kept in sync.

## The Three Stores

| Store | Location | Contents |
|-------|----------|----------|
| Frontmatter YAML | Issue body | Structured metadata including roadmap steps as YAML |
| Body table | Issue body | NOT present in v2 - body contains only frontmatter |
| Comment table | Separate GitHub comment | Markdown table with step references |

## Critical Distinction

**V2 body contains only YAML frontmatter.** The markdown table with step references lives in a separate comment body (`V2_COMMENT_BODY`).

This is different from v1 format where the body contained both frontmatter and the markdown table.

## Test Implications

When writing test assertions for v2 objectives:
- Assertions about YAML data target the body
- Assertions about markdown tables target the comment body
- Do NOT expect `"| - | #777 |"` patterns in the body - those live in comment body

## Update Implications

Functions that update v2 roadmap data must update:
1. Frontmatter YAML in body (via `update_step_in_frontmatter()`)
2. Comment table (via `_replace_table_in_text()`)

Both must implement identical auto-clear/auto-infer semantics.

## Source

See `V2_BODY` and `V2_COMMENT_BODY` test fixtures in `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py` for canonical examples of the format structure.
```

---

### MEDIUM Priority

#### 5. Validation vs Silent Skipping Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
## Validation Guard Clause Anti-Pattern

- action: "writing validation checks using .startswith() or similar guard clauses"
  warning: "Ensure ELSE branch explicitly fails validation rather than silently skipping. Pattern `if value.startswith('#'):` should be `if not value.startswith('#'): raise ValidationError(...)` in validation contexts."

### The Problem

Guard clauses like `if step.plan.startswith("#")` that silently skip non-conforming values can mask data corruption. Invalid data passes through undetected.

### The Fix

In validation contexts, convert guard-and-skip patterns to explicit validation failures:

```python
# BAD: silently skips invalid data
if step.plan and step.plan.startswith("#"):
    # validate...

# GOOD: explicitly fails on invalid data
if step.plan:
    if not step.plan.startswith("#"):
        errors.append(f"Step {step.id} plan '{step.plan}' missing '#' prefix")
    else:
        # validate...
```

### Source

This anti-pattern was discovered in Check 3 of `validate_objective()`. See Check 9 in `src/erk/cli/commands/objective/check_cmd.py` for the corrected pattern.
```

---

#### 6. Auto-Clear Semantics Documentation

**Location:** `docs/learned/cli/commands/update-roadmap-step.md`
**Action:** UPDATE
**Source:** [PR #7151]

**Draft Content:**

```markdown
## Auto-Clear Semantics

When `--pr` is explicitly set without `--plan`, the plan column is automatically cleared in all three stores:

1. **Frontmatter YAML**: `plan: null`
2. **Body table**: Plan column set to `-`
3. **Comment table**: Plan column set to `-`

This ensures consistency across all stores and prevents divergence where the frontmatter shows "no plan" but the table shows a stale plan reference.

### Example

```bash
# Step 1.2 currently has plan=#200
erk exec update-roadmap-step 7132 --step 1.2 --pr "#7147"
# Result: plan auto-cleared in all stores, PR set to #7147
```

### Why Auto-Clear?

When a PR is submitted for a step, the plan that led to that PR is considered complete. Clearing the plan column prevents confusion about whether the plan is still active.

### Source

See `_replace_table_in_text()` and `_replace_step_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` - grep for "Auto-clear plan when PR is explicitly set" to find the implementation.
```

---

#### 7. PR Review Batch Workflow

**Location:** `docs/learned/pr-operations/batch-review-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: PR Review Batch Workflow
read-when:
  - addressing PR review comments
  - using pr-address or pr-preview-address commands
  - resolving multiple review threads
---

# PR Review Batch Workflow

Complete workflow for addressing PR review feedback in batches.

## Workflow Steps

1. **Preview**: Run `/erk:pr-preview-address` to see actionable items without making changes
2. **Check for plan review**: If PR has `erk-plan-review` label, use plan-review-specific workflow
3. **Classify feedback**: Task tool with `pr-feedback-classifier` skill distinguishes inline threads from discussion comments
4. **Display batched plan**: Group related fixes together for efficient execution
5. **Execute by batch**: For each batch: Fix -> Test -> Commit -> Resolve threads
6. **Reply to summary**: After resolving inline threads, reply to bot's summary discussion comment

## Batch Thread Resolution

Use JSON stdin for bulk resolution:

```bash
echo '[{"thread_id": "PRRT_abc", "comment": "Fixed"}, {"thread_id": "PRRT_def", "comment": "Applied"}]' | erk exec resolve-review-threads
```

## Source

See the `pr-address` slash command in `.claude/commands/` for the complete workflow implementation.
```

---

#### 8. V2 Body Structure Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## V2 Objective Body Structure

- action: "writing test assertions for v2 objectives"
  warning: "V2 body contains only YAML frontmatter (no markdown tables). Markdown tables live in V2_COMMENT_BODY. Target assertions to the correct location based on format."

### Common Mistake

Expecting markdown table patterns like `"| - | #777 |"` in the v2 body when they actually live in the comment body.

### Source

See `V2_BODY` and `V2_COMMENT_BODY` test fixtures in `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py`.
```

---

#### 9. Check 9 in Semantic Check Table

**Location:** `docs/learned/objectives/objective-roadmap-check.md`
**Action:** UPDATE
**Source:** [PR #7151]

**Draft Content:**

Add to the "Why Each Semantic Check Exists" table:

```markdown
| Check | Description | Rationale |
|-------|-------------|-----------|
| Plan/PR `#` prefix format | All plan/PR refs must start with `#` | Catches unprefixed references that don't auto-link in GitHub and can cause silent validation skips |
```

---

#### 10. Condition Simplification Pattern

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7151]

**Draft Content:**

```markdown
## Truthiness Simplification

When checking optional values for truthiness, `if x is not None and x:` is redundant. Use just `if x:`.

### Why

Both `None` and empty string `""` are falsy in Python. If you want to distinguish between them, use explicit checks:
- `if x is not None:` - true for any non-None value including empty string
- `if x:` - true only for truthy values (non-empty strings, non-zero numbers, etc.)

For parameters like `new_pr: str | None` where:
- `None` means preserve existing
- `""` means clear
- `"#123"` means set value

Use `if new_pr:` to check for "set value" case, since both `None` and `""` are falsy.
```

---

#### 11. Discussion Comment Reply Pattern

**Location:** `docs/learned/pr-operations/discussion-comment-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Discussion Comment Reply Pattern
read-when:
  - completing PR review address workflow
  - after resolving inline review threads
---

# Discussion Comment Reply Pattern

After resolving inline PR review threads, reply to the bot's summary discussion comment to close the feedback loop.

## Why This Matters

Automated reviewers (like Dignified Code Simplifier) post:
1. Inline comments on specific lines
2. A summary discussion comment listing all issues

Resolving inline threads doesn't automatically indicate completion. Reply to the summary to signal the review is addressed.

## Command

```bash
erk exec reply-to-discussion-comment --pr <number> --comment-id <id> --body "Addressed all feedback"
```

## Source

See the `pr-address` slash command for the complete workflow that includes this step.
```

---

### LOW Priority

#### 12. Post-PR-Submit Push Failure Pattern

**Location:** `docs/learned/erk/pr-submission-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Expected Push Failures After PR Submission

When `erk pr submit` runs, it creates a remote commit ("WIP: Prepare for PR submission"). If the agent continues working locally before pushing, `git push` will fail with non-fast-forward error.

### This is expected behavior.

**Resolution**: Use the `sync-divergence` skill:
1. Load skill: invoke `erk:sync-divergence`
2. Follow workflow: fetch -> diagnose -> rebase -> track -> restack -> submit

### Source

See the `sync-divergence` skill for the complete resolution workflow.
```

---

#### 13. Module Location Discovery Pattern

**Location:** `docs/learned/reference/module-discovery.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
title: Module Location Discovery
read-when:
  - searching for Python modules in monorepo
  - when Glob fails to find expected modules
---

# Module Location Discovery in Monorepo

When Glob patterns fail to locate a Python module, use the import trick:

```bash
python3 -c "import erk_shared.gateway.github.metadata.roadmap; print(erk_shared.gateway.github.metadata.roadmap.__file__)"
```

## When to Use

- Glob pattern `**/modulename.py` returns no results
- Module might be in an unexpected package location
- Monorepo has multiple packages with similar structures

## Why This Works

Python's import system resolves the actual file path regardless of where it lives in the directory structure.
```

---

#### 14. Git Rebase Cherry-Pick Skip Behavior

**Location:** `docs/learned/reference/git-rebase-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Git Rebase Patterns
read-when:
  - rebasing after erk pr submit
  - seeing "skipped previously applied commit" warnings
---

# Git Rebase Cherry-Pick Skip Behavior

When rebasing after `erk pr submit` has created a remote commit, git automatically skips local commits that are already applied to the remote.

## The Message

```
skipped previously applied commit abc1234
hint: use --reapply-cherry-picks to include skipped commits
```

## This is Normal

The remote "WIP: Prepare for PR submission" commit often contains the same changes as your local commit. Git detects this and skips the duplicate.

## No Action Required

This is informational. The rebase completes successfully with no manual intervention needed.
```

---

#### 15. Batch Thread Resolution JSON Pattern

**Location:** `docs/learned/pr-operations/batch-review-workflow.md` (same as item 7)
**Action:** UPDATE (included in item 7)
**Source:** [Impl]

Already included in the batch workflow documentation above.

---

## Contradiction Resolutions

No contradictions detected. All existing documentation is internally consistent with the implementation.

---

## Stale Documentation Cleanup

No stale documentation detected. All code references in existing docs were verified:
- `docs/learned/tui/plan-row-data.md` - all refs valid
- `docs/learned/tui/column-addition-pattern.md` - all refs valid
- `docs/learned/tui/data-contract.md` - all refs valid
- `docs/learned/cli/commands/update-roadmap-step.md` - all refs valid

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Dual-Write Divergence

**What happened:** YAML frontmatter showed `plan: null` but markdown table showed `7146`. The `update_step_in_frontmatter()` function had auto-clear logic when PR was set, but `_replace_table_in_text()` and `_replace_step_refs_in_body()` preserved existing plan values.

**Root cause:** Three update functions evolved independently without a pattern requiring semantic consistency.

**Prevention:** When implementing auto-clear/auto-compute logic, audit ALL write paths that touch the same data. Write integration tests verifying all stores produce identical output for the same operation.

**Recommendation:** TRIPWIRE

### 2. Graphite Cache Staleness

**What happened:** After running `git rebase`, `gt restack` failed with "diverged from tracking" error.

**Root cause:** Raw git operations that change commit SHAs don't automatically update Graphite's internal cache.

**Prevention:** Always run `gt track --no-interactive` immediately after raw git operations (rebase, cherry-pick, reset).

**Recommendation:** TRIPWIRE

### 3. Validation Guard Clause Hiding Invalid Data

**What happened:** Plan value `7146` (without `#` prefix) passed validation because Check 3 used `if step.plan.startswith("#")` as a guard, silently skipping non-`#` values.

**Root cause:** Guard clause pattern that skips rather than validates.

**Prevention:** Convert guard clauses in validation to explicit validation failures. Check for invalid states and report errors rather than using optimistic guards.

**Recommendation:** TRIPWIRE

### 4. Test Assertion Targeting Wrong V2 Location

**What happened:** Test `test_v2_pr_auto_clears_plan_in_all_stores` failed because assertion expected markdown table in `body`, but v2 format stores tables in `comment_body`.

**Root cause:** Misunderstanding of v2 format structure.

**Prevention:** Read test fixtures to understand format structure before writing assertions. Document v2 format clearly.

**Recommendation:** ADD_TO_DOC

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Dual-Write Consistency Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** Before implementing functions that update roadmap data (frontmatter, body table, comment table)

**Warning:** "Audit ALL write paths for semantic consistency. Auto-clear/auto-infer/auto-compute logic must be replicated across all locations. Write integration tests that verify all three stores produce identical output for the same logical operation."

**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the pattern has caused bugs twice now (status auto-inference and plan auto-clear), affects multiple stores that must stay synchronized, and creates data corruption that is difficult to detect without comparing all three stores.

### 2. Graphite Cache Invalidation After Rebase

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** After running git rebase, git cherry-pick, or git reset

**Warning:** "Always run `gt track --no-interactive` immediately to update Graphite's internal cache (.graphite_cache_persist). Without this, `gt restack` will fail with 'diverged from tracking' errors."

**Target doc:** `docs/learned/erk/tripwires.md`

This is tripwire-worthy because the connection between raw git operations and Graphite cache is non-obvious, the error message doesn't clearly indicate the solution, and it affects any workflow that uses both git and Graphite commands.

### 3. Validation vs Silent Skipping

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** When writing validation checks using .startswith() or similar guard clauses

**Warning:** "Ensure ELSE branch explicitly fails validation rather than silently skipping. Pattern `if value.startswith('#'):` should be `if not value.startswith('#'): raise ValidationError(...)` in validation contexts."

**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the pattern appears correct on first glance but has subtle failure modes, invalid data passes silently rather than being caught, and the pattern appears in many validation contexts.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. V2 Body Structure for Tests

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Critical for test assertions but limited to test code scope. If this pattern causes repeated test failures, it should be promoted to a full tripwire.

### 2. Module Location Discovery

**Score:** 2/10 (Non-obvious +2)

**Notes:** Useful reference pattern but low frequency. More appropriate as a reference doc than a tripwire.

### 3. Post-PR-Submit Push Failures

**Score:** 2/10 (Non-obvious +2)

**Notes:** Expected behavior but could be confusing first time. The sync-divergence skill handles this well; documenting in the PR submission workflow should suffice.

### 4. Discussion Comment Reply Pattern

**Score:** 2/10 (Non-obvious +2)

**Notes:** PR operations pattern for workflow completion. Better as procedural documentation than a tripwire warning.