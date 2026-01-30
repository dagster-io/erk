# Plan: Consolidated Documentation from 5 Learn Plans

> **Consolidates:** #6287, #6286, #6283, #6280, #6277

## Source Plans

| #    | Title                                                  | Items Merged |
| ---- | ------------------------------------------------------ | ------------ |
| 6287 | Audit & Clean Remaining Git ABC Methods                | 3 items      |
| 6286 | Consolidate Reminder Hooks                             | 3 items      |
| 6283 | Refactor changelog-update to use subagent              | 6 items      |
| 6280 | Changelog Update Plan                                  | 2 items      |
| 6277 | Auto-Close Review PRs on Plan Close/Implement          | 5 items      |

## What Changed Since Original Plans

- All referenced PRs (#6275, #6278, #6279, #6282, #6285) have landed on master
- AGENTS.md line 160 already updated by PR #6278 (removes "also" reference) - Item 1 from #6286 is DONE
- changelog-update.md refactored from 334→109 lines; categorization rules now in commit-categorizer agent
- Git ABC reduced to exactly 10 abstract property accessors (pure facade pattern)

## Investigation Findings

### Corrections to Original Plans

- **#6287**: PrintingGit had 16 methods removed (14 convenience + 2 rebase), not just 14
- **#6286**: AGENTS.md line 160 already correct - no update needed (already done in PR #6278)
- **#6283**: changelog-update.md is 109 lines (not 120 as stated)
- **#6280**: Categorization rules now live in commit-categorizer agent, not in command file
- **#6277**: All code/tests complete; only documentation items remain

### Overlap Analysis

- **#6283 + #6280**: Both propose changelog documentation. Merged into unified changelog docs (Steps 5-7)
- **#6283 + #6280**: Both reference categorization rules - single doc covers both
- **#6283 session tripwires**: Unique to #6283, kept as separate items (Step 12)

## Remaining Gaps

All source plans have their code implementations complete. Only documentation items remain:
- 8 new docs to create
- 5 existing docs to update

## Implementation Steps

### Step 1: Update `docs/learned/architecture/gateway-abc-implementation.md` _(from #6287)_

**File:** `docs/learned/architecture/gateway-abc-implementation.md`

**Action:** Add "ABC Method Removal Pattern" section

**Content outline:**
1. When to remove: dead convenience methods with zero production callers
2. The 5-place synchronization requirement: abc.py, real.py, fake.py, dry_run.py, printing.py
3. Caller migration: `git.method()` → `git.subgateway.method()`
4. Reference PR #6285 as canonical example
5. Verification: grep across packages for removed method names

**Source:** Investigation of Git ABC showing 10 abstract members after cleanup

### Step 2: Update `docs/learned/architecture/flatten-subgateway-pattern.md` _(from #6287)_

**File:** `docs/learned/architecture/flatten-subgateway-pattern.md`

**Action:** Add "Removed Convenience Methods Rationale" section

**Content outline:**
1. Pure facade goal: Git ABC should contain ONLY property accessors
2. 16 methods removed from PrintingGit (14 convenience + 2 rebase)
3. Before/after examples: `git.get_current_branch()` → `git.branch.get_current_branch()`
4. Periodic audit recommendation for accumulated dead code

**Source:** Investigation showing complete method migration mapping

### Step 3: Update `docs/learned/architecture/tripwires.md` _(from #6287)_

**File:** `docs/learned/architecture/tripwires.md`

**Action:** Add "ABC Method Removal Synchronization" tripwire

**Content:**
```
Action: "removing an abstract method from a gateway ABC"
Warning: "Must remove from 5 places simultaneously: abc.py, real.py, fake.py, dry_run.py, printing.py. Partial removal causes type checker errors. Update all call sites to use subgateway property. Verify with grep across packages."
```

### Step 4: Create `docs/learned/hooks/reminder-consolidation.md` _(from #6286)_

**File:** `docs/learned/hooks/reminder-consolidation.md`

**Action:** CREATE

**Content outline:**
1. Decision framework: UserPromptSubmit (session-wide) vs PreToolUse (action-specific)
2. Why consolidate: token efficiency, signal-to-noise, better targeting
3. dignified-python example: consolidated from 3-tier to 2-tier delivery
4. Prevention checklist: audit existing hooks before adding new reminder paths
5. Capability-gated design: `.erk/capabilities/` marker files

**Frontmatter read_when:**
- "adding a new coding standards reminder"
- "deciding between UserPromptSubmit and PreToolUse hooks for reminders"
- "debugging duplicate reminder output"

### Step 5: Update `docs/learned/hooks/tripwires.md` _(from #6286)_

**File:** `docs/learned/hooks/tripwires.md`

**Action:** Add reminder deduplication tripwire

**Content:**
```
CRITICAL: Before adding new coding standards reminders → Check if reminder is already injected via PreToolUse hook before adding to UserPromptSubmit. Duplicate reminders increase noise and waste tokens. Read reminder-consolidation.md first.
```

### Step 6: Update `docs/learned/architecture/context-injection-tiers.md` _(from #6286)_

**File:** `docs/learned/architecture/context-injection-tiers.md`

**Action:** Update "Integration Example: dignified-python" section (lines 79-87)

**Change:** Replace 3-tier example with 2-tier example. Add historical note explaining PR #6278 removed Per-Prompt tier. Link to reminder-consolidation.md.

### Step 7: Create `docs/learned/changelog/categorization-rules.md` _(from #6283, #6280)_

**File:** `docs/learned/changelog/categorization-rules.md`

**Action:** CREATE (merges items from both #6283 and #6280)

**Content outline:**
1. Category hierarchy: Major Changes, Added, Changed, Fixed, Removed
2. Decision tree for categorization (from #6280)
3. Exclusion patterns: local-only commands, internal tooling, gateway methods, scope markers
4. Commit consolidation guidelines for multi-commit features (from #6280)
5. Roll-up detection patterns
6. Reference: authoritative rules in `.claude/agents/changelog/commit-categorizer.md`

**Frontmatter read_when:**
- "categorizing changelog entries"
- "updating CHANGELOG.md"

### Step 8: Create `docs/learned/reference/changelog-standards.md` _(from #6280)_

**File:** `docs/learned/reference/changelog-standards.md`

**Action:** CREATE

**Content outline:**
1. Commit reference formats: single `(a1b2c3d)`, multiple `(a1b2c3d, e4f5g6h)`, large features
2. Entry structure: standard vs major change entries
3. Keep a Changelog compliance: user focus, past tense, logical grouping
4. Sync marker format: `<!-- As of: \`COMMIT_HASH\` -->`
5. Marker lifecycle: parsing, querying, updating

### Step 9: Update `docs/learned/planning/agent-delegation.md` _(from #6283)_

**File:** `docs/learned/planning/agent-delegation.md`

**Action:** Add changelog-update example as "Context Reduction" pattern

**Content:** New example showing:
- Problem: 2000+ lines of commit JSON in main conversation
- Solution: Delegate to commit-categorizer subagent returning 50-100 line proposal
- Context reduction: 95%
- Output format: STATUS header + compact proposal
- When to apply: large input data, deterministic rules, compact output

### Step 10: Create `docs/learned/architecture/fail-open-patterns.md` _(from #6277)_

**File:** `docs/learned/architecture/fail-open-patterns.md`

**Action:** CREATE

**Content outline:**
1. Pattern definition: non-critical operations fail without blocking the workflow
2. Key insight: identify critical vs non-critical steps
3. Implementation: asymmetric failure handling with metadata consistency
4. Canonical example: `cleanup_review_pr()` in `src/erk/cli/commands/review_pr_cleanup.py`
   - Comment failure: cosmetic, continue
   - PR close failure: critical, return None, preserve metadata
   - Metadata clear: only after close succeeds
5. When to use vs fail-closed vs fail-fast

**Frontmatter tripwire:**
```
Action: "implementing a cleanup operation that modifies metadata based on external API success"
Warning: "Use fail-open pattern. If critical step fails, do NOT execute dependent steps that modify persistent state."
```

### Step 11: Update `docs/learned/planning/lifecycle.md` _(from #6277)_

**File:** `docs/learned/planning/lifecycle.md`

**Action:** Two updates:

**Phase 4 (before line 603):** Add section clarifying review PRs do NOT block implementation. Implementation can proceed regardless of review PR state.

**Phase 5 (after line 662):** Add section on review PR auto-closure during landing:
- Step 2.8: cleanup_review_pr() called after merge
- Fail-open semantics: land succeeds even if cleanup fails
- Metadata archived: review_pr → last_review_pr
- Also note that `erk plan close` triggers same cleanup

### Step 12: Update `docs/learned/sessions/tripwires.md` _(from #6283)_

**File:** `docs/learned/sessions/tripwires.md`

**Action:** Add 2 tripwires:

1. **Session location mismatch:** "Session IDs in metadata may not match available local files. Verify session paths exist before preprocessing."
2. **Large session overflow:** "Sessions exceeding 20,000 tokens are automatically chunked into multi-part files. Analysis must detect and handle chunking."

### Step 13: Run `erk docs sync` to regenerate auto-generated files

After all documentation changes, run `erk docs sync` to regenerate:
- `docs/learned/index.md`
- `docs/learned/tripwires-index.md`
- Category tripwire files

## Items Intentionally Excluded

These items from the original plans were deprioritized as low-value or overly speculative:

- `docs/learned/architecture/agent-output-formats.md` (from #6283) - Single example not enough to establish pattern doc
- `docs/learned/architecture/session-resilience.md` (from #6283) - Session-specific, not broadly applicable
- `docs/learned/sessions/session-analysis-patterns.md` (from #6283) - Low priority, archival
- `docs/learned/commands/changelog-commands.md` (from #6283) - Redundant with categorization-rules.md
- `docs/learned/architecture/plan-cleanup-functions.md` (from #6277) - Covered by fail-open-patterns.md
- `docs/learned/cli/plan-close-pr-closure.md` (from #6277) - Covered by lifecycle.md updates
- Source code docstring updates for land_cmd.py/close_cmd.py (from #6277) - Code already has clear comments

## Attribution

| Source | Steps |
| ------ | ----- |
| #6287  | Steps 1, 2, 3 |
| #6286  | Steps 4, 5, 6 |
| #6283  | Steps 7 (partial), 9, 12 |
| #6280  | Steps 7 (partial), 8 |
| #6277  | Steps 10, 11 |

## Verification

1. Run `erk docs sync` and verify no errors
2. Check that new docs have valid frontmatter with `read_when` conditions
3. Grep `docs/learned/` for broken cross-references
4. Verify tripwires-index.md regenerated with updated counts