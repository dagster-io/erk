# Documentation Plan: Unify plan checkout with `erk br co --for-plan` and `--new-slot`

## Context

This plan consolidates plan checkout into a single unified command (`erk br co --for-plan`) with a `--new-slot` flag for forced slot allocation. Previously, four separate commands handled different aspects of plan checkout; now one command with flags handles resolution, branch creation, and `.impl/` setup. The implementation affected 45+ files across CLI, TUI, tests, and documentation.

The most significant learning from this work is a systematic pattern of **documentation drift** - property reference tables in `docs/learned/planning/next-steps-output.md` fell behind as new properties were added to `IssueNextSteps` and `DraftPRNextSteps` classes. The review bot caught 3 separate instances of incomplete tables. Additionally, the user corrected the agent's understanding of scope: the "prefer branch names over --for-plan" pattern only applies to the draft PR backend (where branches exist upfront), not the issue backend (where branches are created at checkout time).

Future agents will benefit from understanding: (1) the breaking change that removed `erk br create --for-plan`, (2) the backend-specific checkout patterns for draft PR vs issue workflows, (3) the branch name availability hierarchy for generating user-facing commands, and (4) the documentation drift problem that requires proactive table updates when modifying frozen dataclasses.

## Raw Materials

PR #7795

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 14    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Documentation Drift Detection Tripwire

**Location:** `docs/learned/universal-tripwires.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## Documentation Drift for Dataclass Properties

When modifying frozen dataclasses that have `@property` methods, documentation may contain property reference tables that need updating.

**Pattern:** Dataclasses with properties often have corresponding tables in `docs/learned/` that enumerate available properties. When properties are added or removed, these tables become stale.

**Before modifying dataclasses with properties:**
1. Grep for the class name in `docs/learned/`
2. Check if any matching docs contain property tables
3. Update tables to match the new property set

**Example classes with property tables:**
- `IssueNextSteps` - documented in `docs/learned/planning/next-steps-output.md`
- `DraftPRNextSteps` - documented in `docs/learned/planning/next-steps-output.md`

See `packages/erk-shared/src/erk_shared/output/next_steps.py` for property definitions.
```

---

#### 2. Breaking Change: erk br create --for-plan Removal

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## Removed Commands

### erk br create --for-plan (Removed in PR #7795)

**NEVER use `erk br create --for-plan`.** This command was removed and replaced with `erk br co --for-plan`.

**Migration:** Replace all occurrences:
- Old: `erk br create --for-plan 123`
- New: `erk br co --for-plan 123`

**Scope of impact:** CLI output, documentation, TUI commands, slash commands, tutorials. The PR updated 45+ files to migrate to the new syntax.

See `src/erk/cli/commands/branch/checkout_cmd.py` for the current implementation.
```

---

#### 3. Checkout Command Consolidation

**Location:** `docs/learned/cli/checkout-helpers.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7795]

**Draft Content:**

```markdown
## Unified Plan Checkout

Plan checkout is now consolidated into `erk br co` with flags instead of separate commands.

### Command Syntax

- `erk br co <branch>` - Simple branch checkout
- `erk br co --for-plan <issue-number>` - Resolve issue/PR, create branch, setup `.impl/`
- `erk br co --for-plan <issue-number> --new-slot` - Force new slot allocation

### What --for-plan Does

1. Parses the issue identifier
2. Resolves to a Plan via plan_store
3. Derives branch name from plan metadata
4. Creates or fetches the branch (backend-specific)
5. Checks out the branch
6. Sets up `.impl/` folder with plan-ref.json

### Mutual Exclusivity

`BRANCH` argument and `--for-plan` flag are mutually exclusive. Provide one or the other.

See `src/erk/cli/commands/branch/checkout_cmd.py` for implementation.
```

---

#### 4. Backend-Specific Checkout Patterns

**Location:** `docs/learned/planning/backend-checkout-patterns.md`
**Action:** CREATE
**Source:** [Impl] - Session fb6f5596-part2

**Draft Content:**

```markdown
---
read-when:
  - implementing plan checkout features
  - generating checkout commands for different backends
  - deciding between branch name and --for-plan syntax
---

# Backend-Specific Checkout Patterns

Plan backends have different branch creation timing, which affects checkout command generation.

## Draft PR Backend

- **Branch creation:** Upfront when plan is saved (PR created with branch)
- **At checkout time:** Branch already exists remotely
- **Preferred syntax:** `erk br co <branch-name>` (cleaner)
- **Fallback:** `erk br co --for-plan <pr-number>` still works

Branch name is available via `pr_head_branch` in plan metadata.

## Issue Backend

- **Branch creation:** At first checkout (branch doesn't exist at plan-save time)
- **At checkout time:** Branch must be created
- **Required syntax:** `erk br co --for-plan <issue-number>` for first checkout
- **After first checkout:** `erk br co <branch-name>` works (branch now exists)

Branch name follows pattern `P{issue}-{slug}-{timestamp}` and is only known after creation.

## UX Implication

When generating next-steps or user-facing commands:
- Draft PR backend: Prefer actual branch name when available
- Issue backend: Must use `--for-plan` for initial checkout guidance

See `src/erk/cli/commands/branch/checkout_cmd.py` for backend detection logic.
```

---

#### 5. Branch Name Availability Hierarchy

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] - Session fb6f5596-part1

**Draft Content:**

```markdown
## Branch Name Generation

### Availability Hierarchy

When generating checkout commands or next-steps, check branch name availability in order:

1. `worktree_branch` - Actual branch in existing worktree (most reliable)
2. `pr_head_branch` - Branch from PR metadata (available for draft PR backend)
3. Inferred from issue - Computed via `derive_branch_name_from_title()` (may not match actual)

**Pattern:** Prefer actual branch name when available. Only fall back to `--for-plan` syntax when no branch name is known.

**Implementation:** The TUI already implements this pattern in `src/erk/tui/app.py` and `src/erk/tui/commands/registry.py`. Extend this pattern to CLI output and next-steps generation.
```

---

### MEDIUM Priority

#### 6. Slot Allocation: Stack-in-Place vs New-Slot

**Location:** `docs/learned/erk/slot-pool-architecture.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7795]

**Draft Content:**

```markdown
## Slot Allocation Strategies

### Stack-in-Place (Default)

When checking out a plan branch from within an assigned slot, the default behavior is to **stack in place** - reuse the current slot for the new branch.

**Detection:** `_find_current_slot_assignment()` checks if cwd matches an assigned slot path.

**Behavior:** Calls `update_slot_assignment_tip()` to update the slot's tip branch without allocating a new slot.

### New Slot (--new-slot Flag)

To force allocation of a new slot even when in an assigned slot, use `--new-slot`.

**Use case:** Parallel implementations where you want separate worktrees for each branch.

**Behavior:** Calls `allocate_slot_for_branch()` to get a fresh slot regardless of current location.

See `src/erk/cli/commands/branch/checkout_cmd.py` for the decision logic.
```

---

#### 7. .impl/ Setup After Plan Checkout

**Location:** `docs/learned/planning/impl-folder-setup.md`
**Action:** CREATE
**Source:** [Impl] + [PR #7795]

**Draft Content:**

```markdown
---
read-when:
  - implementing plan checkout features
  - understanding .impl/ folder creation
  - debugging plan context issues
---

# .impl/ Folder Setup

When `--for-plan` is used with `erk br co`, the command sets up the `.impl/` folder after successful checkout.

## Setup Contents

- `.impl/plan.md` - The plan content from the GitHub issue/PR
- `.impl/plan-ref.json` - Metadata linking to the source plan

## plan-ref.json Structure

Contains:
- `provider` - Plan backend type (github, draft_pr)
- `plan_id` - Issue or PR number
- `url` - GitHub URL to the plan
- `objective_id` - Associated objective (if any)

## Script Mode Behavior

When run in script mode, `_setup_impl_for_plan()` outputs an activation script and exits instead of printing confirmation messages.

See `src/erk/cli/commands/branch/checkout_cmd.py` function `_setup_impl_for_plan()` for implementation.
```

---

#### 8. Bot False Positive Patterns

**Location:** `docs/learned/reviews/bot-false-positives.md`
**Action:** CREATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
---
read-when:
  - tuning dignified-code-simplifier rules
  - reviewing bot feedback patterns
  - addressing false positive reports
---

# Bot False Positive Patterns

Common patterns that trigger bot reviews but don't require action.

## Mutually Exclusive Branch Variables

When the same variable is assigned in mutually exclusive if/else branches, the bot may flag it as a simplification opportunity. This is often intentional for clarity.

**Example:** Variable assigned differently in `if backend == "draft_pr"` vs `else` block.

## Ternary vs Explicit Conditional

Bot may suggest ternary expressions for simple conditionals. Accept when it improves readability; reject when the conditional has side effects or complex expressions.

## Already-Resolved Thread Comments

CI/bot discussion comments that correspond to already-resolved review threads don't need action. The verification phase should recognize these as non-actionable.

See session impl-85cbf89c for examples of correct interpretation.
```

---

#### 9. Next-Steps Property Tables Verification

**Location:** `docs/learned/planning/next-steps-output.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## Property Tables (Updated PR #7795)

### IssueNextSteps Properties

| Property | Description |
|----------|-------------|
| `prepare` | `erk br co --for-plan <num>` |
| `prepare_and_implement` | Combined prepare + implement |
| `prepare_new_slot` | `erk br co --for-plan <num> --new-slot` |
| `prepare_new_slot_and_implement` | Combined new slot + implement |

### DraftPRNextSteps Properties

| Property | Description |
|----------|-------------|
| `prepare` | `erk br co --for-plan <num>` (or branch name when available) |
| `prepare_and_implement` | Combined prepare + implement |
| `prepare_new_slot` | `erk br co --for-plan <num> --new-slot` |
| `prepare_new_slot_and_implement` | Combined new slot + implement |

See `packages/erk-shared/src/erk_shared/output/next_steps.py` for property definitions.
```

---

#### 10. Ternary Expression Preference

**Location:** `.claude/skills/dignified-python.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## Ternary Expressions

For simple conditional assignments, prefer ternary expressions over nested if-else:

**Preferred:**
```python
value = "yes" if condition else "no"
```

**Avoid:**
```python
if condition:
    value = "yes"
else:
    value = "no"
```

Exception: Use if-else when branches have side effects or complex multi-line logic.
```

---

#### 11. Generator Expression with next()

**Location:** `.claude/skills/dignified-python.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## First Match Pattern

When searching for the first item matching a condition, prefer `next()` with generator:

**Preferred:**
```python
match = next((item for item in collection if item.matches(criteria)), None)
```

**Avoid:**
```python
match = None
for item in collection:
    if item.matches(criteria):
        match = item
        break
```

The generator form is more concise and idiomatic Python.
```

---

### LOW Priority

#### 12. Verification Phase Interpretation

**Location:** `docs/learned/pr-operations/pr-address.md`
**Action:** UPDATE
**Source:** [Impl] - Session 85cbf89c

**Draft Content:**

```markdown
## Verification Phase Notes

After resolving review threads, the verification classifier may still return "actionable" items. Before taking action, check if these are:

- **CI/bot discussion comments** - These correspond to already-resolved review threads and don't need action
- **Automated checks** - CI status comments that are informational only

The agent correctly interprets these as non-actionable when the underlying review threads have been resolved.
```

---

#### 13. update-pr-description Silent Execution

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] - Session 85cbf89c

**Draft Content:**

```markdown
## Command Output Expectations

### erk exec update-pr-description

This command produces **no stdout on success**. This is expected behavior, not a failure indication.

Agents should not interpret lack of output as an error.
```

---

#### 14. Command Organization Updates

**Location:** `docs/learned/cli/command-organization.md`
**Action:** UPDATE
**Source:** [PR #7795]

**Draft Content:**

```markdown
## Plan Checkout Commands

Plan checkout is now unified under `erk br co`:

- `erk br co --for-plan <num>` - Replaces the removed `erk plan co` and `erk br create --for-plan`
- `erk br co --for-plan <num> --new-slot` - Force new slot allocation

The separate `erk plan checkout` command has been removed.
```

---

## Contradiction Resolutions

No contradictions detected. Existing documentation is consistent with the pre-unification model. Updates are needed to reflect the new unified command model, but there are no conflicting statements to resolve.

## Stale Documentation Cleanup

No stale documentation requiring deletion. All code references in existing docs verified as current. The documentation updates are additive or corrective, not removals.

## Prevention Insights

### 1. Scope Creep in Backend Patterns

**What happened:** Agent initially planned to change both draft PR and issue backend paths to prefer branch names over `--for-plan`.

**Root cause:** Incomplete understanding of when branches exist in each backend's lifecycle.

**Prevention:** Draft PR backend creates branches upfront; issue backend creates branches at checkout time. The "prefer branch names" pattern only applies to draft PR backend.

**Recommendation:** ADD_TO_DOC (backend-checkout-patterns.md created above)

### 2. Documentation Table Staleness

**What happened:** Property tables in `next-steps-output.md` were incomplete after new properties were added to `IssueNextSteps` and `DraftPRNextSteps`.

**Root cause:** No automated validation linking documentation tables to source code properties.

**Prevention:** Add universal tripwire requiring grep check before modifying dataclasses with properties.

**Recommendation:** TRIPWIRE (documented in tripwire candidates below)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Documentation Drift for Dataclass Properties

**Score:** 8/10 (Non-obvious: +2, Cross-cutting: +2, Destructive potential: +2, Repeated pattern: +2)

**Trigger:** Before modifying frozen dataclasses with `@property` methods

**Warning:** Check if `docs/learned/` contains property reference tables for this class. Update tables to match new properties. Grep for class name in `docs/learned/` to find docs.

**Target doc:** `docs/learned/universal-tripwires.md`

This is the highest-value finding from the PR. The review bot caught 3 separate instances of drift in property tables. The pattern applies across all dataclasses with documented properties: when properties are added or removed, corresponding documentation tables become stale immediately. Without a tripwire, this silent drift accumulates until someone notices incorrect documentation.

### 2. Breaking Change: erk br create --for-plan Removal

**Score:** 6/10 (Non-obvious: +2, Cross-cutting: +2, Destructive potential: +2)

**Trigger:** Before writing plan checkout commands or documentation

**Warning:** NEVER use `erk br create --for-plan` (removed in #7795). Use `erk br co --for-plan <num>` instead. Applies to CLI output, docs, TUI, slash commands.

**Target doc:** `docs/learned/planning/tripwires.md`

This breaking change affected 45+ files. Agents relying on old documentation or training data will attempt to use the removed command. The tripwire prevents perpetuating outdated syntax in new code or docs.

### 3. Branch Name Availability Hierarchy

**Score:** 5/10 (Non-obvious: +2, Cross-cutting: +2, Repeated pattern: +1)

**Trigger:** Before generating next-steps commands or user-facing checkout guidance

**Warning:** Check data availability for branch names: prefer actual branch name (`worktree_branch` or `pr_head_branch`) over `--for-plan` syntax when available. See branch name availability hierarchy.

**Target doc:** `docs/learned/planning/tripwires.md`

The user explicitly corrected the agent's understanding during implementation. The TUI already implements this pattern correctly in multiple places. Extending it consistently requires awareness of the availability hierarchy.

### 4. Backend-Specific Checkout Patterns

**Score:** 4/10 (Non-obvious: +2, Cross-cutting: +2)

**Trigger:** Before implementing plan checkout features for different backends

**Warning:** Draft PR backend can use `erk br co <branch>` (branch exists upfront). Issue backend requires `erk br co --for-plan <num>` at first checkout (branch created with issue number). Don't apply draft PR patterns to issue backend.

**Target doc:** `docs/learned/planning/tripwires.md`

User correction in session part 2 prevented scope creep by clarifying that the "prefer branch names" pattern only applies to draft PR backend. This distinction is non-obvious and affects UX decisions.

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. Verification Phase Interpretation (Bot Comments)

**Score:** 3/10 (Non-obvious: +2, External tool quirk: +1)

**Notes:** The agent got this right without documentation. After review threads are resolved, remaining CI/bot discussion comments are non-actionable. Low severity since agents handle this correctly, but documenting it prevents future confusion. May not need full tripwire status.

### 2. update-pr-description Silent stdout

**Score:** 2/10 (Non-obvious: +2)

**Notes:** Minor UX detail. The command produces no output on success. Documenting this prevents agents from misinterpreting silence as failure. Too minor for tripwire status; a note in pr-operations tripwires suffices.
