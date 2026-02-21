# Documentation Plan: Consolidate draft-PR workflow documentation and standardize plan branch naming from slash to hyphen

## Context

This learn plan captures knowledge from PR #7705, a documentation-focused PR that consolidated draft-PR workflow documentation and clarified branch naming patterns. The PR added 4 new documentation files and updated 14 existing files, introducing comprehensive coverage of automated review systems, test coverage detection heuristics, Graphite divergence detection patterns, and draft-PR workflow safeguards.

The implementation sessions revealed important operational patterns for PR feedback workflows, including a sophisticated 5-phase structure for addressing PR comments, subagent isolation techniques, and Graphite divergence resolution strategies. Multiple PR review threads from automated bots (audit-pr-docs) provided valuable insights about documentation quality patterns - highlighting risks like behavioral conventions without spec backing, call-site implementation details that drift, and verbatim code copies.

This plan prioritizes completing documentation gaps identified through gap analysis: strengthening tripwires around test location requirements, documenting the PR feedback workflow phases centrally, adding batch thread resolution examples, and codifying documentation drift prevention patterns. The plan also addresses minor stale language (branch-name-inference.md using "plan-" when code uses "planned/") and incomplete tripwire text fixes.

## Raw Materials

PR #7705 materials available in: `.erk/scratch/sessions/034b6f91-e470-4d3b-bc64-418681a93046/learn-agents/`

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 14    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. Batch Thread Resolution Stdin Pattern

**Location:** `docs/learned/pr-operations/draft-pr-handling.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Batch Thread Resolution

When resolving multiple review threads after addressing PR feedback, use the batch resolution command with JSON via stdin:

The `erk exec resolve-review-threads` command accepts a JSON array of thread objects via stdin. Each object requires `thread_id` and `comment` fields. This approach makes a single API call instead of individual calls per thread, improving efficiency and reducing rate limit exposure.

See `src/erk/cli/commands/exec/scripts/resolve_review_threads.py` for implementation details.
```

---

#### 2. Test Location Requirements Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7705]

**Draft Content:**

```markdown
## Test File Location

- **Before placing test files**: Test files MUST live in `tests/**/` directory to be detected by the test-coverage-review bot. No other locations are searched.
  - WARNING: The bot does NOT search `packages/*/tests/` or any other location
  - Tests placed elsewhere will appear as "missing coverage" even if they exist
  - See `.erk/reviews/test-coverage.md` for the authoritative search specification
```

---

#### 3. Auto-Force Behavior for Plan Implementations

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7705]

**Draft Content:**

```markdown
## Plan Implementation Force Behavior

- **When implementing plans**: Plan implementations automatically bypass divergence checks. The submit pipeline uses `effective_force = state.force or is_plan_impl`.
  - This is intentional: plan implementations should proceed without manual intervention
  - If a plan implementation fails, the entire workflow should be retried, not manually force-pushed
  - See `src/erk/cli/commands/pr/submit_pipeline.py` for the auto-force logic
```

---

#### 4. Fix Remaining Test Location Inconsistency

**Location:** `docs/learned/ci/test-coverage-detection.md`
**Action:** UPDATE
**Source:** [PR #7705]

**Draft Content:**

The tripwire warning text at the top of this file still mentions `packages/*/tests/**` as a searched location. Update to match the corrected table:

- Remove any reference to `packages/*/tests/**` from tripwire text
- Clarify that ONLY `tests/**/` is searched
- Ensure consistency between the tripwire section and the table in "Test Location" section

---

#### 5. Graphite Divergence Resolution with gt sync

**Location:** `docs/learned/erk/graphite-divergence-detection.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Alternative Resolution: gt sync --force

When `gt submit` fails with "Branch has been updated remotely", an alternative to manual rebase is:

1. `gt sync --force --no-interactive` - pulls remote and integrates changes via Graphite
2. `gt submit --force --no-interactive` - force pushes the reconciled state

This approach is safer than manual `git rebase` because Graphite handles the merge logic internally. The `--force` flag is required when sync would skip branches in non-interactive mode.

Note: Both `--force` and `--no-interactive` are required. The `--force` flag alone does not disable prompts.
```

---

### MEDIUM Priority

#### 6. PR Feedback Workflow 5-Phase Structure

**Location:** `docs/learned/pr-operations/pr-feedback-workflow-phases.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing PR address commands
  - understanding PR feedback workflow structure
  - building command orchestration with subagents
---

# PR Feedback Workflow Phases

The `/erk:pr-address` command implements a multi-phase workflow for addressing PR review comments. Understanding this structure is essential for command authors and debugging.

## Five-Phase Structure

### Phase 1: Classification

Invoke `pr-feedback-classifier` skill via explicit Task tool (not skill invocation) to categorize feedback items. Uses model: haiku for efficiency.

### Phase 2: Batched Execution Plan Display

Present classified items grouped by type (actionable review threads, discussion comments, already-addressed items) before execution.

### Phase 3: Batch-by-Batch Execution

Execute fixes for each batch with commits after each batch. Maintains atomic, reviewable changes.

### Phase 4: Thread Resolution

Use `erk exec resolve-review-threads` with JSON array via stdin for batch resolution of addressed threads.

### Phase 5: Final Verification

Verify all threads resolved, run `pr-feedback-classifier` again to confirm no remaining actionable items.

## Source Reference

See the `/erk:pr-address` command implementation for the complete workflow.
```

---

#### 7. Subagent Isolation via Task Tool

**Location:** `docs/learned/commands/subagent-isolation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - creating commands that invoke subagents
  - using --print mode with context: fork
  - debugging subagent context isolation issues
---

# Subagent Isolation Patterns

When commands need to invoke subagents in `--print` mode, explicit Task tool invocation provides stronger isolation than skill invocation.

## The Problem

Using `context: fork` metadata in command files does not guarantee complete isolation. In `--print` mode, the forked context may still share state with the parent.

## The Solution

Use explicit Task tool invocation with specific model selection:

- Invoke the Task tool directly (not skill invocation)
- Specify model explicitly (e.g., `model: "haiku"` for classification tasks)
- Set `subagent_type: "general-purpose"` for isolation

## When to Use

- Classification tasks that should not affect parent state
- Read-only analysis that precedes destructive operations
- Any subagent work in `--print` mode commands

## Source Reference

See `/erk:pr-address` command for an example of this pattern with `pr-feedback-classifier`.
```

---

#### 8. False Positive Detection Procedure

**Location:** `docs/learned/pr-operations/pr-address-workflows.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## False Positive Detection Procedure

When automated review bots flag code, follow this procedure before making changes:

1. **Read the flagged code** - Examine the actual code at the flagged location
2. **Check for existing pattern** - Verify if the correct pattern already exists nearby (same function, same class, adjacent lines)
3. **If false positive** - Reply to the thread explaining why no change is needed rather than making unnecessary code changes
4. **If genuine issue** - Proceed with the fix

This prevents unnecessary changes that add noise to git history when bots miss existing correct patterns.
```

---

#### 9. Review Thread Persistence Across Syncs

**Location:** `docs/learned/pr-operations/pr-address-workflows.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Review Thread Persistence

Resolved review threads survive `gt sync --force` operations when the fixes are already on the remote branch. This is expected behavior:

- GitHub tracks thread resolution state independently of commit history
- When you resolve a thread and commit the fix, the resolution persists
- Even if `gt sync --force` pulls different commit SHAs, the thread stays resolved
- No need to re-resolve threads after sync operations

This allows safe divergence resolution without losing PR feedback progress.
```

---

#### 10. Silent Command Verification Pattern

**Location:** `docs/learned/cli/output-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Silent Commands Require Verification

Some erk exec commands produce no output on success. For these commands, always follow with an explicit verification step:

| Command | Verification |
|---------|-------------|
| `erk exec update-pr-description` | `gh pr view <number> --json title,body` |

When building commands that wrap silent operations, include verification in the workflow rather than assuming success from lack of error output.
```

---

#### 11. Documentation Drift Prevention Patterns

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [PR #7705]

**Draft Content:**

```markdown
## Drift Prevention Patterns

PR review feedback from audit-pr-docs revealed three common drift patterns:

### 1. Behavioral Conventions Without Spec Backing

Documenting implementation behavior (e.g., "Authority Level: Enforcing") as if it were a machine-readable specification field creates drift risk when behavior changes without updating docs.

**Prevention:** Note when something is a behavioral convention vs a spec field.

### 2. Call-Site Implementation Details

Tables showing exact parameter order, line numbers for specific call sites, or implementation details of internal functions go stale on refactoring.

**Prevention:** Reference the function/class conceptually; let readers grep for current location.

### 3. Verbatim Code Copies

Copying code blocks directly creates maintenance burden and silent staleness.

**Prevention:** Use source pointers per this document's existing guidance.
```

---

#### 12. CLI Command Verification Requirement

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7705]

**Draft Content:**

```markdown
## CLI Command Documentation

- **When documenting CLI commands**: Always verify command syntax against source code. Do not rely on memory or previous documentation.
  - Commands evolve; documentation from memory may reference old argument names
  - Grep for the command in source to confirm current interface
  - Check `--help` output if available
```

---

### LOW Priority

#### 13. Graphite Cache Mismatch After Raw Git

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Raw Git Operations in Graphite Repos

- **After raw git operations that change SHAs**: Always run `gt track` before `gt restack`.
  - Raw git operations (rebase, reset, amend) change commit SHAs outside Graphite's awareness
  - `.graphite_cache_persist` still points to old SHAs until `gt track` updates it
  - Running `gt restack` without `gt track` first causes "diverged from tracking" errors
  - Sequence: `git rebase ...` -> `gt track` -> `gt restack --no-interactive`
```

---

#### 14. Branch Naming Consistency

**Location:** `docs/learned/planning/branch-name-inference.md`
**Action:** UPDATE
**Source:** [Gap Analysis]

**Draft Content:**

Lines 61-70 of this file use "plan-" in prose when the code uses "planned/" prefix. Update to use "planned/" consistently to match the actual implementation in `packages/erk-shared/src/erk_shared/naming.py`.

---

## Contradiction Resolutions

### 1. Branch Naming Pattern: Slash vs Hyphen

**Existing doc:** `docs/learned/erk/branch-naming.md`, `docs/learned/planning/draft-pr-plan-backend.md`
**Conflict:** The plan title "standardize plan branch naming from slash to hyphen" suggests a code change, but all code uses "planned/" (with slash) consistently.
**Resolution:** The plan title is misleading. This is a documentation-only PR (#7705) that documents existing patterns. No code changes were made or intended. The minor stale language in `branch-name-inference.md` (using "plan-" instead of "planned/") should be updated for consistency, but this is a documentation fix, not a contradiction in the codebase.

## Stale Documentation Cleanup

No stale documentation with phantom references detected. All existing documentation references current, valid code artifacts.

Minor stale language exists in `docs/learned/planning/branch-name-inference.md` (lines 61-70) using "plan-" when code uses "planned/" - addressed in LOW priority item #14.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Graphite Cache Mismatch After Raw Git

**What happened:** After `git rebase origin/$BRANCH`, running `gt restack` produced "diverged from tracking" errors.
**Root cause:** Raw git rebase changed commit SHAs, but Graphite's `.graphite_cache_persist` file still referenced old SHAs. Graphite didn't know the commits had changed.
**Prevention:** Always run `gt track` after any raw git operation that changes commit SHAs, before running any Graphite stack operations.
**Recommendation:** TRIPWIRE - Score 7/10, meets threshold

### 2. Documentation Inconsistency After Partial Fix

**What happened:** PR thread #3 showed that fixing a table in test-coverage-detection.md left inconsistent tripwire text at the top of the same file.
**Root cause:** When fixing an inaccuracy, agent fixed only the first occurrence without checking for other mentions of the same concept.
**Prevention:** When correcting documentation inaccuracies, grep for all occurrences of the concept being corrected within the file and across related files.
**Recommendation:** TRIPWIRE - Score 6/10, meets threshold

### 3. Unnecessary Code Changes from False Positive Bot Feedback

**What happened:** Session showed agent reading flagged code, discovering the correct pattern already existed nearby, and replying instead of making unnecessary changes.
**Root cause:** Automated bots cannot always detect if the correct pattern exists elsewhere in the same function or class.
**Prevention:** Always read flagged code and verify pattern doesn't already exist before making changes. Reply to explain false positives.
**Recommendation:** TRIPWIRE - Score 6/10, meets threshold

### 4. gt submit Divergence After PR Review Fixes

**What happened:** After committing fixes, `gt submit` failed with "Branch has been updated remotely".
**Root cause:** Remote branch had updates (from automation or parallel work) that weren't fetched before the local commit.
**Prevention:** In PR review workflows, always run `gt sync --force --no-interactive` before final `gt submit`.
**Recommendation:** ADD_TO_DOC - Pattern documented but not tripwire-level severity

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Multiple Mentions Checking When Fixing Documentation

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before fixing documentation inaccuracies
**Warning:** "When correcting an inaccurate statement in documentation, grep for all occurrences of that concept in the file. Fixing only the first instance creates inconsistency."
**Target doc:** `docs/learned/documentation/tripwires.md`

This tripwire addresses a common failure mode where partial fixes leave documentation internally inconsistent. The test-coverage-detection.md file showed this exact issue: the table was corrected but tripwire text at the top still mentioned the wrong locations. Readers following the tripwire text would get incorrect guidance while the table showed correct information.

### 2. False Positive Detection Before Code Changes

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before making code changes based on automated review bot feedback
**Warning:** "Read the flagged code first and verify if the suggested pattern already exists nearby. If it's a false positive, reply to explain rather than making unnecessary changes."
**Target doc:** `docs/learned/pr-operations/tripwires.md`

Automated review bots provide valuable feedback but cannot always detect if the correct pattern exists in adjacent code. Making changes based on bot feedback without verification adds unnecessary noise to git history and can introduce bugs by duplicating existing logic.

### 3. Graphite Cache Mismatch After Raw Git Operations

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2, External tool quirk +1)
**Trigger:** After raw git operations that change commit SHAs in Graphite repo
**Warning:** "Always run `gt track` after raw git operations (rebase, reset, amend) before running `gt restack`. Raw git changes SHAs outside Graphite's awareness - `.graphite_cache_persist` still points to old SHAs."
**Target doc:** `docs/learned/erk/tripwires.md`

This is the highest-scoring tripwire candidate because the failure mode is completely non-obvious, affects all Graphite operations after any raw git SHA change, and can corrupt Graphite stack state requiring manual recovery. The session demonstrated this exact issue: after `git rebase`, running `gt restack` without `gt track` first produced confusing "diverged from tracking" errors.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Files Must Live in tests/**

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** Already documented in testing docs, but PR comments show confusion persists. May warrant stronger emphasis as tripwire if confusion continues. Currently addressed via documentation update rather than tripwire addition.

### 2. Silent Command Verification

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** General CLI pattern affecting multiple commands. Not error-prone enough for tripwire status - commands don't fail silently, they just don't output on success. Pattern documented in CLI output patterns.

### 3. CLI Command Documentation Verification

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** Good documentation practice but only one occurrence in PR comments. Would promote to tripwire if multiple instances of memory-based command documentation causing issues.

### 4. gt sync Before gt submit in PR Workflows

**Score:** 3/10 (criteria: Cross-cutting +2, External tool quirk +1)
**Notes:** Specific to PR review workflows where remote may have changed. The gt sync alternative is documented but not tripwire-level because gt submit's error message is clear about the problem.
