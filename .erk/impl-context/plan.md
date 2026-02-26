# Documentation Plan: Simplify PR checkout to eliminate erk pr sync dependency

## Context

This PR (#8238) simplifies the PR checkout workflow by making `erk pr checkout` self-sufficient for the standard plan-save-dispatch-checkout flow. Previously, users had to run `erk pr checkout 123 && erk pr sync --dangerous` to ensure their local branch matched the remote state after a dispatched implementation. The new approach fetches from remote and force-updates the local branch automatically, eliminating the need for the separate sync step.

The documentation opportunities span three key areas: (1) user-facing workflow changes that affect how engineers interact with erk, (2) architectural patterns around gateway abstraction and when to bypass it, and (3) testing patterns that changed with the new fetch-always behavior. Future agents implementing similar checkout or branch alignment features would benefit from understanding when force-updates are appropriate, how Graphite integration was simplified, and the tripwires around direct gateway access.

The sessions also revealed broader insights about refactoring discipline: how to detect vestigial commands, when simplification should lead to deletion rather than abstraction preservation, and systematic patterns for command removal. These meta-patterns are valuable for any future simplification work.

## Raw Materials

PR #8238

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 15 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 5 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. BranchManager abstraction bypass pattern

**Location:** `docs/learned/architecture/branch-manager-abstraction.md`
**Action:** UPDATE
**Source:** [PR #8238]

**Draft Content:**

```markdown
## When to Bypass the Abstraction

The BranchManager ABC provides a unified interface for branch operations across Git and Graphite backends. However, some operations intentionally bypass this abstraction:

### Force-Update Operations

`branch_manager.create_branch()` does not support a `force` parameter because it's designed for creating new branches, not aligning existing ones. When you need to force-update a local branch to match remote state:

**Correct pattern:**
```python
# Alignment operation - bypass abstraction
ctx.git.branch.create_branch(branch_name, force=True)
```

**Why not add force to BranchManager?** Force-update is a Git-specific alignment operation, not a branch creation. The abstraction's purpose is to provide consistent creation semantics, not to wrap every possible Git operation.

See `src/erk/cli/commands/pr/checkout_cmd.py` for the `_fetch_and_update_branch` helper implementing this pattern.
```

---

#### 2. PR checkout workflow change

**Location:** `docs/learned/cli/pr-checkout-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing checkout commands
  - debugging post-dispatch checkout issues
  - understanding erk pr sync deprecation
---

# PR Checkout Workflow

## Current Behavior (Post-#8238)

`erk pr checkout` is self-sufficient for the standard plan-save-dispatch-checkout workflow:

```bash
# Plan saved, dispatched to remote, now checking out
source "$(erk pr checkout 123 --script)"
```

The command:
1. Fetches from remote (always, even if local branch exists)
2. Force-updates local branch to match remote state
3. Tracks/retracks with Graphite as needed
4. Does NOT submit to remote (no force-push)

## Previous Behavior (Deprecated)

Before #8238, checkout required a separate sync step:

```bash
source "$(erk pr checkout 123 --script)" && erk pr sync --dangerous
```

The sync performed heavyweight operations (gt sync, squash, restack) that frequently failed with sibling worktree conflicts.

## When `erk pr sync` Is Still Useful

The sync command remains available for edge cases:
- Non-plan branches needing manual Graphite reconciliation
- Explicit request for squash/restack operations

See `src/erk/cli/commands/pr/sync_cmd.py` docstring for current guidance.
```

---

#### 3. Simplified Graphite integration in checkout

**Location:** `docs/learned/cli/pr-checkout-graphite.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - modifying checkout Graphite integration
  - debugging Graphite tracking after checkout
  - understanding submit vs retrack operations
---

# Graphite Integration in PR Checkout

## Deferred Operations Pattern

Checkout no longer submits to remote. Heavy operations are deferred:

| Operation | When Performed |
|-----------|----------------|
| Track untracked branch | Checkout (when parent is None) |
| Retrack diverged branch | Checkout (when SHA diverged from Graphite cache) |
| Squash, restack | `erk land` or `erk pr submit` |
| Submit to remote | `erk land` or `erk pr submit` |

## Retrack Logic

After remote dispatch, the local Graphite cache has stale SHA information. Checkout detects this:

```python
if ctx.graphite.is_branch_diverged_from_tracking(branch_name):
    ctx.graphite_branch_ops.retrack_branch(branch_name)
```

This updates the local Graphite metadata without pushing to remote.

## Track vs Retrack

- **Track**: Branch has no Graphite parent (first-time tracking)
- **Retrack**: Branch is tracked but SHA cache is stale (post-dispatch)

See `src/erk/cli/commands/pr/checkout_cmd.py` for implementation.
```

---

#### 4. Vestigial command detection criteria

**Location:** `docs/learned/refactoring/vestigial-command-detection.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - evaluating whether a command should be deleted
  - implementing simplification PRs
  - reviewing deletion proposals
tripwires: 6
---

# Vestigial Command Detection

## Detection Criteria

A command is a strong deletion candidate when ALL THREE signals are present:

1. **Self-declaration**: Command's docstring explicitly states it's "no longer needed" or recommends alternatives
2. **Zero programmatic invocations**: Grep `.claude/` for skills and commands - if no automation calls it, users aren't dependent on programmatic access
3. **Documentation always lists alternatives**: Every doc reference pairs the command with a recommended replacement

## Verification Grep Pattern

```bash
# Check for programmatic invocations (escape hyphen to avoid false matches)
grep -r "erk pr sync[^-]" .claude/

# Check doc references
grep -r "erk pr sync" docs/
```

The `[^-]` prevents matching `erk pr sync-divergence` when searching for `erk pr sync`.

## Deletion vs Deprecation

- **Delete immediately** when all three criteria met and no user workflows depend on it
- **Deprecate first** when users may have external scripts (add warning, wait one release)

For internal-only tools like erk, immediate deletion is usually safe.
```

---

#### 5. Fix stale example in status-indicators.md

**Location:** `docs/learned/tui/status-indicators.md`
**Action:** UPDATE
**Source:** [PR #8238]

**Draft Content:**

The example at line 36 shows `compute_status_indicators` returning `"rocket"` but actually returns `"eyes rocket"` for `is_draft=False`. Fix by either:
- Changing example to use `is_draft=None` (which returns just `"rocket"`)
- Updating the expected return value comment to `"eyes rocket"`

This was pre-existing inaccuracy caught by the audit-pr-docs bot during PR review.

---

### MEDIUM Priority

#### 1. New helper function: `_fetch_and_update_branch`

**Location:** `docs/learned/cli/pr-checkout-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing branch alignment operations
  - debugging post-dispatch checkout issues
---

# PR Checkout Patterns

## Fetch-and-Update Helper

The `_fetch_and_update_branch` helper consolidates branch alignment logic with three cases:

| Scenario | Action |
|----------|--------|
| Remote exists, no local | Create tracking branch |
| Remote exists, local exists | Force-update local to match remote |
| No remote, no local | Fetch via PR ref |

### Why Force-Update?

After remote dispatch, local branches are stale. Force-update ensures local matches remote state without requiring heavyweight sync operations.

### Direct Git Access

This helper uses `ctx.git.branch.create_branch(force=True)` directly because BranchManager doesn't support the force flag. This is an alignment operation, not branch creation.

See `src/erk/cli/commands/pr/checkout_cmd.py` for implementation.
```

---

#### 2. Branch fetching/updating recipe

**Location:** `docs/learned/erk/branch-operations.md`
**Action:** CREATE
**Source:** [PR #8238]

**Draft Content:**

```markdown
---
read-when:
  - implementing branch fetch operations
  - aligning local branches with remote
---

# Branch Operations

## Fetch and Align Pattern

Reusable pattern for ensuring local branch matches remote:

1. **Fetch**: `ctx.git.fetch_branch(remote, branch_name)`
2. **Detect state**: Check if local branch exists
3. **Create or update**:
   - No local: `ctx.branch_manager.create_branch(branch_name, start_point)`
   - Local exists: `ctx.git.branch.create_branch(branch_name, force=True)`

This pattern is used in `_fetch_and_update_branch` helper.

See also: `docs/learned/planning/planned-pr-branch-sync.md` for the three-step sync pattern this reuses.
```

---

#### 3. PR review address workflow

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - modifying pr-address command
  - understanding PR comment classification
---

# PR Review Address Workflow

## Multi-Phase Process

The `/erk:pr-address` command orchestrates automated PR comment response:

1. **Classify feedback**: Load pr-feedback-classifier via Task tool (forked context)
2. **Display batched plan**: Show user what will be changed
3. **Execute batch-by-batch**: Make changes, commit, resolve threads
4. **Verify resolution**: Re-run classifier to confirm all threads resolved
5. **Update PR**: Add session-based summary to PR description

## Subagent Isolation

The classifier skill uses `context: fork` metadata. Invoke via Task tool with explicit parameters rather than direct skill invocation to ensure true isolation.

See `.claude/skills/pr-feedback-classifier/SKILL.md` for classifier implementation.
```

---

#### 4. Mark pr-sync-workflow.md as deprecated

**Location:** `docs/learned/erk/pr-sync-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add deprecation notice at top:

```markdown
> **DEPRECATION NOTICE**: The 8-step sync workflow described here is no longer needed for standard plan-save-dispatch-checkout flows. See `docs/learned/cli/pr-checkout-workflow.md` for the simplified approach. This document remains for edge cases requiring manual Graphite reconciliation.
```

---

#### 5. Test pattern updates for checkout tests

**Location:** `docs/learned/testing/cli-checkout-tests.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing checkout command tests
  - debugging fetch assertion failures
tripwires: 4
---

# Checkout Test Patterns

## Fetch Behavior Assertions (Post-#8238)

**Old pattern (incorrect):**
```python
# Assumed no fetch when branch exists locally
assert len(git.fetched_branches) == 0
```

**New pattern (correct):**
```python
# Fetch is always called, even for existing branches
assert ("origin", "branch-name") in git.fetched_branches
```

## Force-Update Assertions

Verify force-update by checking `git.created_branches` includes force flag.

## Retrack Test Pattern

Test diverged state using:
```python
BranchMetadata(commit_sha="new-sha", tracked_revision="old-sha")
```

Then assert retrack message appears:
```python
assert "Retracking diverged branch" in result.output
```

See `tests/commands/pr/test_checkout_graphite_linking.py` for examples.
```

---

#### 6. Simplification scope decisions

**Location:** `docs/learned/refactoring/simplification-scope.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing simplification PRs
  - deciding between abstraction and deletion
---

# Simplification Scope Decisions

## Prefer Deletion Over Abstraction

When implementing "simplify X" PRs, if the simplification makes other code unnecessary:

- **Expand scope** to delete that code
- **Don't preserve** it in refactored form

## Example: PR #8238

Initial approach: Add `retrack_branch` to BranchManager ABC to properly abstract the call.

User correction: The simplification makes sync unnecessary, so delete the retrack call entirely instead of abstracting it.

## Tension: Incremental vs Aggressive

- **Incremental**: Add abstractions first, delete later (safer, more commits)
- **Aggressive**: Delete if simplification enables it (cleaner, fewer artifacts)

Prefer aggressive when simplification is the explicit goal of the PR.
```

---

### LOW Priority

#### 1. Plan save UX flow

**Location:** `docs/learned/planning/plan-save-ux.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - modifying exit-plan-mode behavior
  - understanding plan save prompts
---

# Plan Save UX Flow

## Three-Option Prompt

When exiting plan mode, the `exit-plan-mode-hook` fires with options:

1. **Create plan PR**: Save to GitHub issue via `/erk:plan-save`
2. **Skip PR and implement here**: Proceed to implementation
3. **View/Edit plan**: Review before deciding

## Trunk-Aware Slot Recommendations

The hook provides context-aware suggestions based on current branch state.

See `.claude/hooks/exit-plan-mode-hook/` for implementation.
```

---

#### 2. Subagent isolation via Task tool

**Location:** `docs/learned/commands/subagent-isolation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - invoking skills with context: fork
  - ensuring subagent isolation
---

# Subagent Isolation via Task Tool

## When to Use Task Tool

When skills have `context: fork` metadata, use explicit Task tool calls instead of direct skill invocation:

```python
# Correct: Task tool with explicit parameters
Task(
    subagent_type="...",
    model="...",
    description="..."
)
```

Direct skill invocation with `--print` mode doesn't provide true isolation for forked-context skills.
```

---

#### 3. Command deletion checklist

**Location:** `docs/learned/cli/command-deletion-checklist.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - removing CLI commands
  - planning command deprecation
---

# Command Deletion Checklist

## Identify Targets

### Deletion Targets
- Command file (`src/erk/cli/commands/.../cmd.py`)
- Command tests (`tests/commands/.../test_cmd.py`)
- Command-specific docs

### Update Targets
- Import statements (parent `__init__.py`)
- Command registrations
- Doc references (grep for command name)

## Verification

1. Run deleted command (should fail)
2. Run alternative command (should work)
3. Run test suite
4. Grep for command name to find stragglers

## CHANGELOG Discipline

Deletions are historical record. CHANGELOG.md does not need updates for command removals.
```

---

#### 4. Iterative bot reviews (living documentation pattern)

**Location:** `docs/learned/ci/review-bot-architecture.md`
**Action:** CREATE
**Source:** [PR #8238]

**Draft Content:**

```markdown
---
read-when:
  - implementing review bots
  - understanding CI comment patterns
---

# Review Bot Architecture

## Living Documentation Pattern

Review bots update comments in-place with activity logs and timestamps rather than creating new comments. This provides:

- Continuous documentation auditing
- Activity history visible in single comment
- Reduced comment noise on PRs

See `.github/workflows/` for bot implementations.
```

---

#### 5. Update BranchManager docs for retrack_branch

**Location:** `docs/learned/architecture/branch-manager-abstraction.md`
**Action:** UPDATE (BLOCKED)
**Source:** [PR #8238]

**Note:** Once `plnd/add-retrack-branch-abc-02-25-2034` merges, add `retrack_branch` to the documented BranchManager API surface area. This item is blocked on that PR.

---

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Inaccurate example in status-indicators.md

**Location:** `docs/learned/tui/status-indicators.md:36`
**Action:** UPDATE_EXAMPLE
**Phantom References:** Example shows `compute_status_indicators` returning `"rocket"` but returns `"eyes rocket"` for `is_draft=False`
**Cleanup Instructions:** Either change example to use `is_draft=None` (returns single emoji) or update the expected return value comment

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Incremental vs Aggressive Refactoring Tension

**What happened:** Initial approach was to add `retrack_branch` to BranchManager ABC to properly abstract the direct gateway call.

**Root cause:** Agent followed safe incremental refactoring pattern without considering whether the simplification made the abstraction unnecessary.

**Prevention:** When implementing "simplify X" PRs, first ask: does this simplification make other code deletable? Prefer deletion over abstraction preservation.

**Recommendation:** ADD_TO_DOC (see simplification-scope.md)

### 2. Vestigial Command Preservation

**What happened:** Agent was cautious about proposing sync command deletion despite evidence it was no longer needed.

**Root cause:** Without clear criteria for "safe to delete", agents err on side of preservation.

**Prevention:** Establish clear tripwire: docstring says "no longer needed" + zero skill/command invocations + docs list alternatives = deletion candidate.

**Recommendation:** TRIPWIRE (see vestigial-command-detection.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Vestigial command detection

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before concluding a command is still needed based on its presence in codebase
**Warning:** Grep for: (1) command docstring saying "no longer needed", (2) zero invocations in .claude/ skills/commands, (3) docs always listing alternatives. All three = strong deletion candidate.
**Target doc:** `docs/learned/refactoring/vestigial-command-detection.md`

This tripwire prevents both premature deletion (missing invocations) and unnecessary preservation (keeping dead code). The grep discipline is essential - checking `.claude/` for programmatic usage is non-obvious but critical.

### 2. BranchManager abstraction bypass

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** Before calling ctx.git.branch methods directly instead of ctx.branch_manager
**Warning:** Check if operation is supported by ctx.branch_manager abstraction. Only bypass for force operations (force-update, force-delete) which aren't abstracted. Add inline comment explaining why.
**Target doc:** `docs/learned/architecture/branch-manager-abstraction.md`

The abstraction exists for a reason, but force operations are a legitimate exception. Without this tripwire, agents either (a) wrongly add force support to the abstraction or (b) bypass without explanation.

### 3. Test assertions for force-update behavior

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before asserting len(git.fetched_branches) == 0 in checkout tests
**Warning:** Old pattern: assert len(git.fetched_branches) == 0 (no fetch when exists). New pattern: fetch always called, assert branch IN fetched_branches.
**Target doc:** `docs/learned/testing/cli-checkout-tests.md`

This behavioral change affects multiple test files. Without the tripwire, agents writing new checkout tests will copy old patterns that no longer match implementation.

### 4. Simplified Graphite integration

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before calling submit_branch during checkout operations
**Warning:** Checkout no longer submits to remote (no force-push). Graphite stack metadata updates deferred to erk land or erk pr submit.
**Target doc:** `docs/learned/cli/pr-checkout-graphite.md`

Understanding the deferred operations pattern is essential for anyone modifying checkout behavior. Without this tripwire, agents may re-add submit calls thinking they're necessary.

### 5. Calling subgateway mutation methods directly

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** Before calling ctx.{subgateway}.{mutation_method}() directly
**Warning:** Check if method exists on BranchManager ABC. If not, add it as abstract method with implementations in Git/Graphite/Fake variants. Never bypass abstraction layer for mutation operations.
**Target doc:** `docs/learned/architecture/branch-manager-abstraction.md`

This was caught by the tripwires bot during PR review. The distinction between read operations (okay to bypass) and mutation operations (should use abstraction) is non-obvious.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Simplification scope decisions

**Score:** 3/10 (criteria: Non-obvious +2, Destructive potential +1)
**Notes:** Pattern applies specifically to "simplify X" PRs, not universally cross-cutting. If more sessions demonstrate scope expansion tension, promote to full tripwire.

### 2. Subagent isolation via Task tool

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** Only applies when skills have `context: fork` metadata. Limited applicability reduces tripwire value. May warrant promotion if more forked-context skills are added.

---

## Cross-Reference Updates Needed

Existing docs that should link to new documentation:

1. **docs/learned/cli/checkout-helpers.md** - Link to new pr-checkout-workflow.md and pr-checkout-patterns.md
2. **docs/learned/erk/pr-sync-workflow.md** - Add deprecation notice, link to new pr-checkout-workflow.md
3. **docs/learned/workflows/plan-implement.md** - Update plan-save-dispatch-checkout workflow description
4. **docs/learned/integrations/graphite-integration.md** - Link to pr-checkout-graphite.md for updated submit/retrack patterns
5. **docs/learned/architecture/gateway-patterns.md** - Link to updated branch-manager-abstraction.md section on force operations
6. **docs/learned/testing/cli-testing-patterns.md** - Link to cli-checkout-tests.md for updated assertion patterns
7. **docs/learned/planning/planned-pr-branch-sync.md** - Link to pr-checkout-patterns.md showing how three-step sync pattern is reused

---

## SHOULD_BE_CODE Recommendations

Items that belong in code artifacts rather than learned docs:

| # | Item | Recommendation | Rationale |
|---|------|----------------|-----------|
| 1 | Branch slug generation formula | Add docstring to slug generation function explaining: 2-4 words, max 30 chars, lowercase-hyphenated, action verbs (add/fix/refactor/update), drop filler words | Single-location insight, mechanical algorithm - belongs in code |
| 2 | Negative test assertions pattern | Add code comment above `assert "foo" not in result` explaining: "Validates dead code stays dead. Can be removed when feature fully removed." | Single-artifact behavior - belongs in test file |
| 3 | BranchManager extension pattern | Add docstring to BranchManager ABC explaining when to add new abstract methods (when sub-gateway methods need exposure for CLI) | Single-class API reference - belongs in ABC |
