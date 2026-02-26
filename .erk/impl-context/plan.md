# Documentation Plan: Add keyboard shortcut (n) to open GitHub Actions run URL from main list

## Context

This plan captures documentation insights from implementing a keyboard shortcut (`n`) to open GitHub Actions run URLs directly from the TUI main list view. The implementation was straightforward — a new `Binding` registration and `action_open_run()` method that mirrors the existing `action_open_pr()` pattern — but it revealed significant documentation gaps around TUI direct actions versus command palette commands.

The sessions also encountered operational challenges that affect all agents: the `${CLAUDE_SESSION_ID}` substitution silently returning empty strings in CI environments, and stale `.impl/plan.md` content requiring recovery from PR body. These cross-cutting concerns warrant tripwires to prevent future confusion.

Future agents implementing TUI keyboard shortcuts need clear guidance on when to use direct action bindings (like `n`, `p`, `r`) versus command palette commands, and a comprehensive inventory of which keys are already claimed. The existing `adding-commands.md` only covers command palette registration, leaving direct actions undocumented.

## Raw Materials

PR #8330: https://github.com/dagster-io/erk/pull/8330

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Session ID unavailable in CI environments

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-def3285d

**Draft Content:**

```markdown
## Session ID Unavailability in CI

<!-- Source: CLAUDE.md, Session ID Access section -->

### Trigger

Before using `${CLAUDE_SESSION_ID}` in CI workflows, hooks, or exec scripts.

### Warning

The `${CLAUDE_SESSION_ID}` substitution returns an empty string in GitHub Actions environments. Commands that depend on session ID will fail silently or produce confusing errors.

### Pattern

Always use graceful degradation with `|| true` suffix for session-dependent commands:

```bash
erk exec impl-signal started --session-id "${CLAUDE_SESSION_ID}" || true
```

### Root Cause

Claude Code session ID is only available in interactive Claude Code sessions. CI workflows run without an active session, so the substitution yields an empty string rather than an error.

### Affected Commands

- `erk exec impl-signal` (all lifecycle phases)
- `erk exec upload-impl-session`
- Any hook or script using `${CLAUDE_SESSION_ID}`
```

#### 2. Direct action vs command palette distinction

**Location:** `docs/learned/tui/direct-actions.md` (NEW FILE)
**Action:** CREATE
**Source:** [Impl] diff-analysis, session-def3285d

**Draft Content:**

```markdown
---
title: Direct Actions
read_when:
  - adding a keyboard shortcut to the TUI main list view
  - deciding between direct action binding and command palette command
  - implementing an action_* method in ErkDashApp
tripwires:
  - action: "registering a simple browser-open or view-switch action in command palette"
    warning: "Consider a direct Binding + action_* method instead. Browser actions benefit from single-key access without palette discoverability overhead."
---

# Direct Actions

Direct actions are keyboard shortcuts that bypass the command palette and execute immediately. They are implemented as `Binding` entries paired with `action_*` methods on `ErkDashApp`.

## When to Use Direct Actions vs Command Palette

| Characteristic | Direct Action | Command Palette |
|----------------|---------------|-----------------|
| Execution time | Instant (browser open, view switch) | May need progress display |
| Complexity | Simple, single operation | May have validation, confirmation |
| Discoverability | Footer key display only | Searchable in palette |
| Key binding | Single key required | Optional shortcut |

**Use direct action when:**
- Opening URLs (browser launch is instant)
- Switching views (toggle-like behavior)
- Refreshing data (single operation)
- Existing parallel pattern uses direct action

**Use command palette when:**
- Operation may take time (needs progress indicator)
- Operation has validation or confirmation steps
- Operation benefits from searchable discoverability
- Multiple variants of same operation exist

## Implementation Pattern

<!-- Source: src/erk/tui/app.py, ErkDashApp.action_open_run -->

Direct actions follow a consistent pattern. See `ErkDashApp.action_open_run()` and `action_open_pr()` in `src/erk/tui/app.py` for examples.

The pattern:
1. Call `_get_selected_row()` to get current selection
2. Return early if no row selected
3. Use LBYL check for optional field (`if field is not None:`)
4. Execute action (browser launch, etc.)
5. Provide user feedback via status bar

## Key Grouping Conventions

Browser-open shortcuts are grouped together in the BINDINGS list. See `src/erk/tui/app.py` BINDINGS for current groupings.
```

#### 3. Keyboard shortcuts inventory

**Location:** `docs/learned/tui/keyboard-shortcuts.md` (NEW FILE)
**Action:** CREATE
**Source:** [Impl] diff-analysis, gap-analysis

**Draft Content:**

```markdown
---
title: Keyboard Shortcuts Inventory
read_when:
  - adding a new keyboard binding to the TUI
  - checking which keys are available
  - understanding existing shortcut patterns
tripwires:
  - action: "adding a new key binding without checking existing bindings"
    warning: "Check keyboard-shortcuts.md inventory first. Key conflicts between app-level and modal bindings can cause confusing behavior."
---

# Keyboard Shortcuts Inventory

This document inventories all keyboard shortcuts on the TUI main list view to help agents avoid conflicts and understand binding patterns.

## Inventory Source

<!-- Source: src/erk/tui/app.py, ErkDashApp.BINDINGS -->

The authoritative source is the `BINDINGS` list in `ErkDashApp`. Grep for `BINDINGS` in `src/erk/tui/app.py` to see the current inventory.

## Key Binding Groups

Bindings are organized by function:

1. **Browser actions** - Open external URLs (`p`, `n`, etc.)
2. **View switching** - Change dashboard view or filter
3. **Navigation** - Move between rows, expand/collapse
4. **Operations** - Execute actions on selected plan

## Adding New Bindings

When adding a new key binding:

1. Check this inventory for conflicts
2. Follow grouping conventions (place browser actions together)
3. Use direct action pattern for instant operations
4. Update footer display text to be concise

## Context-Sensitive Bindings

Some keys have different meanings in different contexts:
- Modal screens can shadow app-level bindings
- Command palette has its own key handling
- Detail screens may reuse keys with different actions

This is by design — `r` means "open run" in detail modal but may mean something else at app level.
```

#### 4. Stale .impl/plan.md recovery pattern

**Location:** `docs/learned/planning/impl-folder-structure.md`
**Action:** UPDATE
**Source:** [Impl] session-def3285d

**Draft Content:**

Add to existing document:

```markdown
## Stale Plan Content Recovery

### Detection

Before implementing from `.impl/plan.md`, validate that the content matches the expected plan:

1. Extract plan title from first H1 heading in `.impl/plan.md`
2. Compare against expected title from PR or issue metadata
3. If mismatch detected, the `.impl/` folder contains stale content from a previous plan

### Recovery Pattern

When stale content is detected, fetch the correct plan from the PR body:

```bash
gh pr view <PR_NUMBER> --json body -q '.body'
```

Parse the plan section from the PR body (typically between `## Implementation Plan` markers) and use that as the authoritative source.

### Root Cause

Stale content occurs when:
- A worktree was reused without cleaning `.impl/`
- A previous plan's content wasn't properly cleaned up after merge
- Branch was reset to an earlier state

### Prevention

The `setup-impl` command should validate plan content matches expected title before proceeding with implementation setup.
```

### MEDIUM Priority

#### 5. Test coverage requirements

**Location:** `docs/learned/testing/coverage-requirements.md` (NEW FILE)
**Action:** CREATE
**Source:** [PR #8330] automated review comments

**Draft Content:**

```markdown
---
title: Test Coverage Requirements
read_when:
  - adding tests for a new feature
  - addressing test-coverage-review bot comments
  - understanding what tests satisfy automated review
tripwires: []
---

# Test Coverage Requirements

This document describes what the automated test-coverage-review bot expects when reviewing PR test coverage.

## Coverage Expectations

The bot checks that:

1. **Success cases are tested** - Primary functionality works as expected
2. **Failure/empty cases are tested** - Edge cases handled gracefully
3. **Test patterns match feature complexity** - Simple features need fewer tests

## Satisfying the Bot

For TUI action methods, the expected pattern is:
- One test for success path (data present, action executes)
- One test for failure path (data missing, graceful handling)

See test patterns in `tests/tui/test_app.py` for examples of test structures that satisfy coverage requirements.

## Internal Helper References

Tests can reference internal helpers (like `_get_selected_row()`) when testing action methods that use them. This is acceptable — the test verifies the public behavior, not the internal implementation.
```

#### 6. PR address workflow examples

**Location:** `docs/learned/pr-operations/pr-address-workflow.md` (NEW FILE or UPDATE if exists)
**Action:** CREATE
**Source:** [Impl] session-07c76130

**Draft Content:**

```markdown
---
title: PR Address Workflow
read_when:
  - addressing PR review comments
  - using /erk:pr-address command
  - responding to automated review bots
tripwires: []
---

# PR Address Workflow

The `/erk:pr-address` command handles PR review comments systematically.

## Simple Single-Comment Reviews

For PRs with minimal feedback (1 actionable comment):

1. **Classify comments** - Distinguish actionable threads from informational bot comments
2. **Address actionable thread** - Make the code change
3. **Reply to bot discussion comments** - Acknowledge fix in discussion thread
4. **Verify CI** - Run fast-ci to confirm no regressions
5. **Update PR** - Push changes and mark threads resolved

## Example Workflow

<!-- Source: session-07c76130 -->

A typical flow for addressing a single LBYL violation:

1. Bot flags `if optional_field:` as truthy check violation
2. Change to `if optional_field is not None:`
3. Reply to bot's discussion comment acknowledging the fix
4. Run pytest with `-k` filter for affected tests
5. Commit and push

## Distinguishing Comment Types

- **Review threads** - Inline code comments requiring resolution
- **Discussion comments** - Bot summaries in conversation thread
- **Check statuses** - CI results (not comments)

Reply to discussion comments even when the underlying review thread is already resolved — this maintains clear PR history.
```

#### 7. Automated bot interaction patterns

**Location:** `docs/learned/pr-operations/bot-interaction.md` (NEW FILE)
**Action:** CREATE
**Source:** [Impl] session-07c76130, PR #8330 comments

**Draft Content:**

```markdown
---
title: Bot Interaction Patterns
read_when:
  - responding to automated review bot comments
  - understanding bot re-run behavior
  - replying to dignified-python or test-coverage bots
tripwires: []
---

# Bot Interaction Patterns

Multiple automated review bots analyze PRs and post comments. This document explains how to interact with them effectively.

## Bot Types

1. **Dignified Python Review** - Checks Python style (LBYL, type annotations)
2. **Test Coverage Review** - Verifies test coverage for changes
3. **Exec Reference Docs** - Checks documentation completeness

## Replying to Bot Comments

When addressing a violation:

1. Fix the code issue in a commit
2. Reply to the bot's **discussion comment** (not just the review thread)
3. Include commit reference in reply: "Fixed in [commit]"

The bot may re-run on subsequent pushes and either update its comment or post a new one.

## Bot Re-Run Behavior

Bots re-analyze on each push. Previous violation comments remain visible even after fixing, but new comments reflect current state.

## Activity Logs

Some bots include activity logs showing what they checked. These are informational — no action required from agents.
```

#### 8. LBYL common violations reference

**Location:** `docs/learned/reviews/automated-review.md` (UPDATE if exists, otherwise CREATE)
**Action:** UPDATE
**Source:** [PR #8330] automated review comments

**Draft Content:**

Add section to existing document:

```markdown
## Common LBYL Violations

Quick reference for violations frequently caught by the Dignified Python Review bot:

### Truthy Checks on Optional Types

**Wrong:**
```python
if optional_string:  # Catches empty string as falsy
    do_something(optional_string)
```

**Correct:**
```python
if optional_string is not None:
    do_something(optional_string)
```

### Dict Key Access

**Wrong:**
```python
if d.get('key'):  # Catches empty/zero values as falsy
    use_value(d['key'])
```

**Correct:**
```python
if 'key' in d:
    use_value(d['key'])
```

### Why This Matters

Truthy checks conflate `None` with empty strings (`""`), zero (`0`), and empty collections. LBYL requires explicit checks that test exactly the condition you care about.
```

### LOW Priority

#### 9. Pre-existing CI failures identification

**Location:** `docs/learned/ci/debugging.md` (UPDATE if exists, otherwise link to existing ci docs)
**Action:** UPDATE
**Source:** [Impl] session-07c76130

**Draft Content:**

Add section:

```markdown
## Identifying Pre-Existing CI Failures

When CI fails during PR review, determine whether failures are related to your changes:

### Detection Pattern

1. Check which files the failing tests touch
2. Compare against your changeset
3. If no overlap, failure is likely pre-existing

### Verification

Run the same CI check on the base branch:
- If it fails there too, the issue predates your PR
- Note the pre-existing failure in PR description
- Do not block PR review fixes on unrelated failures

### Common Pre-Existing Failures

- Flaky tests with timing dependencies
- Format issues in unrelated files
- Documentation sync issues
```

#### 10. setup-impl staging failure handling

**Location:** `docs/learned/planning/impl-folder-structure.md`
**Action:** UPDATE
**Source:** [Impl] session-def3285d

**Draft Content:**

Add note:

```markdown
## Known Non-Fatal Errors

### Staging .erk/impl-context/

The command `git add -f .erk/impl-context/` may fail with exit code 128 if the directory doesn't exist. This occurs on fresh checkouts or when impl-context wasn't created.

This error is **non-fatal** and can be safely ignored. The setup-impl script handles this gracefully.
```

#### 11. `gt submit` "No-op" verification pattern

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-07c76130

**Draft Content:**

Add potential tripwire (score 3, below threshold but worth noting):

```markdown
## gt submit "No-op" Behavior

### Trigger

When `gt submit` reports "No-op".

### Behavior

This message indicates the branch is already synchronized with remote. It does not indicate failure.

### Verification

If confused by "No-op", verify branch state:

```bash
git status  # Shows if branch is ahead/behind remote
git push    # Will report "Everything up-to-date" if truly synced
```

### Root Cause

Graphite's "No-op" message appears when there's nothing to push because the branch was already submitted. This commonly occurs when:
- Previous `gt submit` succeeded
- Manual `git push` was used
- Branch was created from an already-pushed state
```

## Contradiction Resolutions

**None detected.** The gap analysis identified a potential shortcut conflict between app-level `r` (refresh) and command palette `r` (open_run), but these operate in different input contexts and do not conflict at runtime.

## Stale Documentation Cleanup

**None detected.** All referenced documentation has valid file paths. No phantom references found.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Edit Tool Multiple Matches

**What happened:** Edit tool found 3 matches for `if row.run_url:` pattern
**Root cause:** Common code pattern appeared multiple times in file
**Prevention:** Always provide 5-10 lines of surrounding context to uniquely identify target location
**Recommendation:** CONTEXT_ONLY (common Claude Code tool usage, not erk-specific)

### 2. Background Task Timing

**What happened:** TaskOutput failed to find background task that completed immediately
**Root cause:** Short-running commands complete before background monitoring starts
**Prevention:** Use synchronous execution for commands expected to complete quickly
**Recommendation:** CONTEXT_ONLY (command-specific edge case)

### 3. Session ID Empty in CI

**What happened:** `${CLAUDE_SESSION_ID}` substitution returned empty string, causing impl-signal failures
**Root cause:** Claude Code session ID not available in GitHub Actions environment
**Prevention:** Always use `|| true` suffix for session-dependent commands in CI
**Recommendation:** TRIPWIRE (cross-cutting, silent failure, high severity)

### 4. Stale .impl/plan.md Content

**What happened:** `.impl/plan.md` contained content from a previous plan, not the current PR's plan
**Root cause:** Previous plan content not cleaned up during worktree reuse
**Prevention:** Validate plan.md first line matches expected plan title before proceeding
**Recommendation:** TRIPWIRE (destructive potential if implementing wrong plan)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Session ID Unavailable in CI

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using `${CLAUDE_SESSION_ID}` in CI workflows, hooks, or exec scripts
**Warning:** Session ID substitution returns empty string in GitHub Actions. Always use `|| true` suffix for graceful degradation.
**Target doc:** `docs/learned/ci/tripwires.md`

This deserves tripwire status because the failure is completely silent — the substitution yields an empty string rather than an error, and commands continue with invalid state. Multiple commands are affected (`impl-signal`, `upload-impl-session`), making this a cross-cutting concern that agents will encounter repeatedly.

### 2. Stale .impl/plan.md Recovery

**Score:** 4/10 (Non-obvious +2, Destructive potential +2)
**Trigger:** Before implementing a plan from `.impl/`, validate plan.md first line matches expected plan title
**Warning:** If mismatch detected, fetch correct plan from PR body using `gh pr view --json body`.
**Target doc:** `docs/learned/planning/tripwires.md`

Implementing the wrong plan due to stale content could cause significant wasted effort. While not as severe as the session ID issue, the potential for harm justifies tripwire status.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. `gt submit` "No-op" Behavior

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Confusing message but not harmful. The "No-op" is informational, not an error. Additional evidence of agents being blocked by this message would warrant promotion.

### 2. setup-impl Staging .erk/impl-context/

**Score:** 2/10 (Non-obvious +2)
**Notes:** Non-fatal error with exit 128 when directory doesn't exist. Error message is confusing but the system handles it gracefully. Low priority for tripwire.

### 3. Pre-existing CI Failures

**Score:** 2/10 (Non-obvious +2)
**Notes:** Good pattern to document but not a critical tripwire. Agents need to learn to distinguish related vs unrelated failures, but the consequence of confusion is wasted time, not harmful changes.

## Key Insights

### Documentation Effectiveness

The implementation succeeded quickly because existing patterns (`action_open_pr`) provided a clear template. This demonstrates that pattern documentation works — when it exists. The gap is that the *choice* between patterns (direct action vs command palette) isn't documented.

### Cross-Cutting CI Concerns

Session ID unavailability is a fundamental environment difference between local development and CI. This affects any agent-related command that tracks sessions. The graceful degradation pattern (`|| true`) should be standard practice for all such commands.

### Test Pattern Reuse

Both sessions produced excellent test coverage by following existing test patterns. The TUI testing infrastructure (fake providers, pilot testing) is mature and well-documented, enabling efficient test creation.
