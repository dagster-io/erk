# Documentation Plan: Add --sync flag to auto-submit PR checkouts to Graphite

## Context

PR #8261 implemented an opt-in `--sync` flag for the `erk pr checkout` command that automatically runs `gt submit --no-interactive` after checkout when certain conditions are met (new worktree, same-repo PR, Graphite enabled). This eliminates the manual step of linking Graphite's local metadata to existing GitHub PRs after checkout.

The implementation demonstrates several patterns worth documenting: opt-in flag gating for subprocess calls, TUI-CLI coordination for generated shell commands, and exhaustive boolean condition test coverage. The planning and implementation sessions were clean with zero errors, providing good examples of efficient exploration and proper pattern adherence. However, the PR review process required 4 iterations for the automated review bot to achieve complete test coverage, highlighting the importance of comprehensive testing upfront.

Key insights for future agents: CLI flags referenced by TUI command palette entries require coordinated updates, and all new parameters to public functions need explicit test coverage even when they "just thread through" to other functions.

## Raw Materials

Session analysis and diff analysis from PR #8261 implementation.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 12    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. TUI command palette coordination when adding CLI flags [TRIPWIRE]

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8261]

**Draft Content:**

```markdown
## TUI-CLI Flag Coordination

**Trigger:** When adding CLI flags that affect TUI-generated commands

**Warning:** TUI command palette generates shell commands via string interpolation. Missing flag updates cause silent failures where copied commands lack intended functionality.

**Required Action:**
1. Grep for the command name in `src/erk/tui/commands/registry.py`
2. Find `_display_copy_*` functions that reference the command
3. Update generated command strings to include new flags where appropriate

**Example:** Adding `--sync` to `erk pr checkout` required updating `_display_copy_pr_checkout()` to output `source "$(erk pr checkout {pr} --script --sync)"`.

See `src/erk/tui/commands/registry.py` for the display function implementations.
```

---

#### 2. New parameter test coverage requirement [TRIPWIRE]

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8261]

**Draft Content:**

```markdown
## New Parameter Test Coverage

**Trigger:** When adding parameters to public functions

**Warning:** Even parameters that "just thread through" to another function need explicit test coverage. The automated review bot will catch this, but fixing it requires multiple review iterations.

**Required Action:**
1. Write test cases that exercise the new parameter in both truthy and falsy states
2. For boolean parameters, consider truth table coverage (see boolean-logic-coverage.md)
3. Verify the parameter is threaded correctly through the entire call chain

**Why This Matters:** Parameters that thread through multiple function layers can have subtle bugs where the value is dropped or transformed incorrectly. Only explicit tests verify the complete path.

PR #8261 required 4 bot review iterations because `post_cd_commands` parameter threading was initially untested.
```

---

#### 3. pr-address workflow validation case

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** CREATE
**Source:** [PR #8261]

**Draft Content:**

```markdown
---
read-when:
  - responding to automated PR review comments
  - using pr-address command for the first time
  - debugging pr-address workflow issues
tripwires: 0
---

# PR Address Workflow

Documents the pr-address workflow for responding to automated bot review comments.

## Overview

The pr-address workflow enables agents to respond to PR review comments automatically. When triggered, it parses review comments and generates appropriate code changes or responses.

## Production Validation: PR #8261

PR #8261 represents the first production success case of the pr-address workflow responding to automated bot comments:

1. Bot identified missing test coverage for new `post_cd_commands` parameter
2. `erk pr address-remote 8261` was triggered
3. Agent added 3 new test cases addressing the review feedback
4. Bot approved the changes after verification

## Expected Flow

1. Bot posts review comments identifying issues
2. Run `erk pr address-remote <pr-number>` or `/erk:pr-address`
3. Agent parses comments and implements fixes
4. Push changes and await bot re-review
5. Iterate until all comments are resolved

## Iteration Expectations

Bot reviews may require multiple iterations. PR #8261 required 4 iterations from initial review to final approval. This is normal for comprehensive coverage requirements.

See `src/erk/cli/commands/pr/` for pr-address command implementation.
```

---

#### 4. --sync flag for PR checkout with Graphite

**Location:** `docs/learned/cli/pr-checkout-sync-flag.md`
**Action:** CREATE
**Source:** [Plan], [Impl], [PR #8261]

**Draft Content:**

```markdown
---
read-when:
  - implementing checkout commands with automation flags
  - adding Graphite integration to CLI commands
  - understanding opt-in flag patterns
tripwires: 0
---

# PR Checkout --sync Flag

Documents the `--sync` flag for `erk pr checkout` that auto-submits to Graphite after checkout.

## Purpose

Automates the manual step of running `gt submit --no-interactive` after PR checkout to link Graphite's local metadata with the existing GitHub PR.

## Behavior

The flag activates `gt submit` only when ALL conditions are met:
- `--sync` flag is passed
- Creating a new worktree (not switching to existing)
- Same-repo PR (not a fork)
- Graphite is enabled for the repository

If any condition fails, the flag is silently a no-op.

## TUI Integration

The TUI command palette's "checkout && sync" action automatically includes `--sync` in the generated command, providing seamless Graphite integration without user intervention.

## When NOT to Use

- For fork PRs (Graphite doesn't support cross-repo branches)
- When checking out to an existing worktree (already synced)
- When you want to inspect the branch before syncing with Graphite

## Implementation Pattern

The flag demonstrates opt-in gating for subprocess calls:
```python
post_cd_commands=["gt submit --no-interactive"] if should_submit_to_graphite and sync else None
```

This pattern preserves existing safety conditions while adding explicit user consent.

See `src/erk/cli/commands/pr/checkout_cmd.py` for the implementation, grep for `--sync` and `should_submit_to_graphite`.
```

---

### MEDIUM Priority

#### 1. Boolean condition truth table test pattern

**Location:** `docs/learned/testing/boolean-logic-coverage.md`
**Action:** CREATE
**Source:** [PR #8261]

**Draft Content:**

```markdown
---
read-when:
  - testing functions with multiple boolean conditions
  - ensuring comprehensive branch coverage
  - writing tests for conditional behavior
tripwires: 0
---

# Boolean Logic Test Coverage

Documents the truth table approach for exhaustive boolean condition testing.

## Pattern

For functions with N boolean conditions, create 2^N test cases to cover all possible combinations.

## Example: PR #8261

The `--sync` flag behavior depends on two boolean conditions:
1. `should_submit_to_graphite` (derived from: Graphite enabled + new worktree + same-repo)
2. `sync` flag value

This requires 4 tests (2^2):

| should_submit_to_graphite | sync | gt submit called? | Test Case |
|---------------------------|------|-------------------|-----------|
| True | True | Yes | `test_..._includes_gt_submit_for_new_graphite_worktree` |
| True | False | No | `test_..._no_gt_submit_without_sync_flag` |
| False | True | No | `test_..._no_gt_submit_for_fork_prs` |
| False | False | No | `test_..._no_gt_submit_for_existing_worktree` |

## When to Apply

Use truth table coverage when:
- Multiple conditions gate a single behavior
- Edge cases matter (the conditions interact in non-obvious ways)
- Automated review bots require branch coverage

See `tests/commands/pr/test_checkout_graphite_linking.py` for the complete test implementation.
```

---

#### 2. Variable extraction for complex boolean conditions

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8261]

**Draft Content:**

Add to the existing conventions document:

```markdown
## Variable Extraction for Complex Conditions

When a boolean expression combines multiple conditions, extract it into a named variable that describes the intent.

**Before:**
```python
if graphite_enabled and is_new_worktree and not is_fork_pr and sync:
    post_cd_commands = ["gt submit --no-interactive"]
```

**After:**
```python
should_submit_to_graphite = graphite_enabled and is_new_worktree and not is_fork_pr
if should_submit_to_graphite and sync:
    post_cd_commands = ["gt submit --no-interactive"]
```

**Benefits:**
- Single source of truth for the condition
- Self-documenting code (the variable name explains intent)
- Enables reuse without duplicating logic
- Easier to test (can mock the extracted variable)

This pattern was praised in PR #8261 review as exemplary refactoring.
```

---

#### 3. High-parameter function design decisions

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8261]

**Draft Content:**

Add to the existing conventions document:

```markdown
## High-Parameter Functions

When a function has many parameters, choose between two approaches:

### Approach 1: Keyword-Only Marker (`*,`)

Use `*,` to force keyword arguments when:
- Parameters have clear, distinct meanings
- The function is a CLI command handler (parameters come from Click)
- Refactoring would create an awkward abstraction

### Approach 2: Refactor to Dataclass

Refactor to a config/options dataclass when:
- Parameters represent a cohesive concept (e.g., checkout options)
- The same parameter group is passed through multiple call layers
- Parameter count exceeds 7-8

### Example Decision

`navigate_and_display_checkout()` has 11 parameters and uses approach 1 (keyword-only marker) because:
- It's a display orchestration function
- Parameters don't form a cohesive domain concept
- Breaking it up would create artificial abstractions

However, if the same parameter combinations appear across multiple functions, consider extracting a `CheckoutDisplayOptions` dataclass.
```

---

#### 4. Flag gating pattern for opt-in subprocess calls

**Location:** `docs/learned/cli/opt-in-subprocess-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - adding opt-in automation to CLI commands
  - gating subprocess calls with boolean flags
  - implementing conditional post-checkout workflows
tripwires: 0
---

# Opt-in Subprocess Call Pattern

Documents the pattern for making subprocess calls opt-in via CLI flags.

## Pattern

Use boolean AND to gate subprocess calls while preserving existing safety conditions:

```python
post_cd_commands=["command"] if existing_condition and new_flag else None
```

## Benefits

- Preserves existing safety logic unchanged
- Adds explicit user consent via flag
- Maintains clean `None` handling for no-op case
- Avoids nested conditionals

## Example

From `--sync` flag implementation:

```python
# Existing condition: only run for new same-repo worktrees with Graphite
should_submit_to_graphite = graphite_enabled and is_new_worktree and not is_fork_pr

# Add opt-in gating: require explicit --sync flag
post_cd_commands=["gt submit --no-interactive"] if should_submit_to_graphite and sync else None
```

## When to Use

- Automating workflows that have side effects
- Adding features that change default behavior
- Integrating with external tools (Graphite, git, etc.)

See `src/erk/cli/commands/pr/checkout_cmd.py` for the implementation.
```

---

#### 5. TUI command palette patterns for opt-in flags

**Location:** `docs/learned/tui/command-palette-patterns.md`
**Action:** CREATE
**Source:** [Impl], [PR #8261]

**Draft Content:**

```markdown
---
read-when:
  - adding TUI command palette entries
  - deciding whether to auto-include CLI flags in TUI commands
  - coordinating TUI with CLI flag changes
tripwires: 1
---

# TUI Command Palette Patterns

Documents patterns for TUI command palette entries and their coordination with CLI commands.

## Auto-Including UX-Improving Flags

When a CLI flag improves the default user experience, consider auto-including it in TUI-generated commands.

**Example:** The `--sync` flag for PR checkout automates Graphite submission. The TUI "checkout && sync" command includes it automatically:

```python
def _display_copy_pr_checkout(self) -> str:
    return f'source "$(erk pr checkout {self.pr.number} --script --sync)"'
```

## Trade-offs

**Auto-include when:**
- The flag represents the "sensible default" for TUI users
- Omitting it creates friction in common workflows
- The flag has no negative side effects

**Let users add manually when:**
- The flag has trade-offs users should consider
- Different users have different preferences
- The flag is for advanced/debugging use cases

## Coordination Tripwire

When adding CLI flags, always check if TUI references that command. See TUI tripwires for the required update pattern.
```

---

#### 6. Update activation scripts doc for dynamic post-cd commands

**Location:** `docs/learned/cli/activation-scripts.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the existing activation scripts document:

```markdown
## Dynamic Post-CD Commands

Checkout commands can dynamically inject post-CD commands based on runtime conditions.

### How It Works

The `navigate_and_display_checkout()` function accepts an optional `post_cd_commands` parameter. When provided, these commands are embedded in the activation script and execute after `cd` completes.

### Example: Graphite Auto-Submit

```python
# Conditionally inject gt submit into activation script
post_cd_commands=["gt submit --no-interactive"] if should_submit_to_graphite and sync else None

navigate_and_display_checkout(
    ...,
    post_cd_commands=post_cd_commands,
)
```

### Guidelines

- Commands should be idempotent (safe to run multiple times)
- Commands should be fast (user waits for them to complete)
- Commands should fail gracefully (don't block checkout on failure)

See `src/erk/cli/commands/checkout_helpers.py` for the `navigate_and_display_checkout` implementation.
```

---

#### 7. Automated review bot iteration patterns

**Location:** `docs/learned/ci/review-bot-patterns.md`
**Action:** CREATE
**Source:** [PR #8261]

**Draft Content:**

```markdown
---
read-when:
  - understanding automated review bot behavior
  - debugging repeated review iterations
  - setting expectations for PR review cycles
tripwires: 0
---

# Review Bot Iteration Patterns

Documents expected iteration patterns for automated PR review bots.

## Expected Behavior

The automated review bot may require multiple iterations to achieve complete coverage. This is working as designed, not a bug.

## Example: PR #8261

PR #8261 required 4 review iterations over ~1 hour:
1. Initial review: identified missing test coverage
2. Iteration 2: additional test cases added
3. Iteration 3: more comprehensive coverage requested
4. Iteration 4: final approval

## What Triggers Additional Iterations

- Missing test coverage for new parameters
- Incomplete branch coverage for boolean conditions
- Documentation inconsistencies
- Style violations

## Reducing Iteration Count

- Use truth table approach for boolean conditions (see testing/boolean-logic-coverage.md)
- Test all new parameters explicitly, even "pass-through" ones
- Run local linting before pushing
- Review bot feedback from similar PRs for patterns

## When to Escalate

Bot iterations are normal. Escalate only if:
- Feedback is contradictory between iterations
- Bot requests impossible changes
- Iteration count exceeds 6-7 without progress
```

---

### LOW Priority

#### 1. Update shell activation pattern doc

**Location:** `docs/learned/cli/shell-activation-pattern.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add to the existing shell activation pattern document:

```markdown
## Post-CD Command Execution

When using `--script` mode, the activation script can include commands that execute after `cd` completes but before returning control to the user.

This enables automated workflows like:
- Graphite submission (`gt submit --no-interactive`)
- Environment validation
- Tool initialization

Commands are passed via the `post_cd_commands` parameter to checkout helper functions.
```

---

#### 2. Update Graphite branch setup doc

**Location:** `docs/learned/erk/graphite-branch-setup.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add to the existing Graphite branch setup document:

```markdown
## Automated Graphite Submission

The `--sync` flag on `erk pr checkout` automates `gt submit` during checkout. This eliminates the manual step of linking Graphite metadata after checking out PRs.

**Conditions for auto-submit:**
- `--sync` flag passed
- Creating a new worktree
- Same-repo PR (not a fork)
- Graphite enabled for repository

See cli/pr-checkout-sync-flag.md for detailed behavior documentation.
```

---

## Contradiction Resolutions

None detected. The `--sync` flag integrates cleanly with existing patterns (activation scripts, Graphite integration, shell activation) without contradicting any existing documentation.

## Stale Documentation Cleanup

None detected. All referenced code locations exist and are current.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TUI Command Palette Out of Sync with CLI Flags

**What happened:** When adding the `--sync` flag to `erk pr checkout`, the TUI command palette initially didn't include the flag in its generated shell commands.

**Root cause:** TUI generates commands via string interpolation in `_display_copy_*` functions. These functions are separate from CLI command definitions and don't automatically pick up new flags.

**Prevention:** Always grep for command name in `src/erk/tui/commands/registry.py` when adding CLI flags.

**Recommendation:** TRIPWIRE - Add to tui/tripwires.md

### 2. Missing Test Coverage for "Pass-Through" Parameters

**What happened:** The automated review bot caught that the `post_cd_commands` parameter had no explicit test coverage, even though it was correctly threaded through the call chain.

**Root cause:** "Pass-through" parameters seem trivial and are easy to skip testing. However, threading bugs can occur at any layer.

**Prevention:** Write explicit tests for all new parameters, regardless of how simple they appear.

**Recommendation:** TRIPWIRE - Add to testing/tripwires.md

### 3. ExitPlanMode Called Too Early

**What happened:** In the planning session, the agent called ExitPlanMode immediately after creating the implement-now marker. The user rejected this tool call.

**Root cause:** Agent assumed marker creation implied user was ready to proceed. User wanted to review/confirm before exiting plan mode.

**Prevention:** Add explicit pause or user confirmation between marker creation and ExitPlanMode.

**Recommendation:** ADD_TO_DOC - Document in planning patterns

### 4. Edit Before Read Tool Error

**What happened:** Agent attempted to edit a file that hadn't been fully read in the session.

**Root cause:** Used Grep to locate content but didn't follow up with Read before Edit.

**Prevention:** When using Grep to find edit locations, always Read the full file before editing if not already read.

**Recommendation:** CONTEXT_ONLY - Minor error, immediately self-corrected

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. TUI Command Palette Coordination

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1)

**Trigger:** When adding CLI flags that are referenced by TUI command palette entries

**Warning:** TUI command palette generates shell commands via string interpolation in `_display_copy_*` functions. If you add a CLI flag without updating these functions, TUI-generated commands will silently lack the new flag.

**Target doc:** `docs/learned/tui/tripwires.md`

This is highly tripwire-worthy because the failure mode is silent (users get working but incomplete commands) and the connection between CLI and TUI is non-obvious from the code structure. PR #8261 would have shipped with broken TUI commands if this hadn't been caught during implementation planning.

### 2. New Parameter Test Coverage Requirement

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** When adding parameters to public functions

**Warning:** Even "pass-through" parameters that simply thread values through the call chain need explicit test coverage. The automated review bot will request this, requiring additional iteration cycles.

**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because it's counter-intuitive (why test a parameter that just gets passed along?) but the bot enforces it. Better to write tests upfront than iterate through multiple review cycles.

### 3. Script Mode Navigation Post-CD Commands

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** When modifying checkout commands that use script mode

**Warning:** Changes to `navigate_and_display_checkout` signature affect how post-CD commands are threaded. Verify parameter threading through the entire call chain.

**Target doc:** `docs/learned/cli/tripwires.md`

This is borderline tripwire-worthy. The pattern is non-obvious but only applies to a specific subsystem. Worth documenting but may not warrant a prominent warning.

### 4. ExitPlanMode Timing with Implement-Now Marker

**Score:** 4/10 (Non-obvious +2, Silent failure +2)

**Trigger:** When creating implement-now markers in plan mode

**Warning:** Do not call ExitPlanMode immediately after marker creation. Wait for explicit user confirmation - the user may want to review or edit the plan before proceeding.

**Target doc:** `docs/learned/planning/tripwires.md`

This is moderately tripwire-worthy. The user rejection in session a581f45a indicates this is a real usability issue, but it may be specific to plan-mode behavior rather than a general pattern.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. TUI Command Registry Grep Pattern

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Searching for `erk {command}` in `registry.py` is non-obvious the first time but becomes clear after one experience. Would warrant promotion if multiple engineers make the same mistake.

### 2. Graphite Submission Conditions

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)

**Notes:** The combination of conditions (Graphite enabled + new worktree + same-repo PR) is documented but easy to forget one. Would warrant promotion if bugs arise from missing conditions.
