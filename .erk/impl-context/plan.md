# Documentation Plan: Split objective-plan command into inner/outer with pre-marking support

## Context

This plan captures learnings from PR #8176, which refactored the `/erk:objective-plan` workflow to prevent race conditions when multiple parallel sessions attempt to plan for the same objective node. The solution splits the command into an outer command (handles interactive node selection) and an inner command (handles planning with a known node), enabling the CLI to pre-mark nodes as "planning" in Python before Claude starts.

The implementation introduces several reusable patterns: inner/outer command splitting for commands with both interactive and programmatic paths, best-effort state updates that silently fail when agents will retry, and status-only roadmap updates without PR numbers. These patterns are cross-cutting concerns that affect command design, testing, and parallel session coordination throughout the codebase.

Documentation matters because the inner/outer split pattern is non-obvious and deviates from the simpler approach of adding conditional logic within a single command. Future agents creating commands with similar dual paths need guidance on when this architecture is appropriate. Additionally, the test fixture selection between `context_for_test` and `erk_isolated_fs_env` caused subtle issues that warrant a tripwire to prevent future confusion.

## Raw Materials

PR #8176

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Inner/Outer Command Split Pattern

**Location:** `docs/learned/commands/inner-outer-command-pattern.md`
**Action:** CREATE
**Source:** [Impl], [PR #8176]

**Draft Content:**

```markdown
---
read-when:
  - creating commands with both interactive selection and programmatic invocation
  - optimizing commands for parallel session coordination
  - considering whether to add conditional logic within a command markdown
tripwires: 2
---

# Inner/Outer Command Split Pattern

## When to Use

Split a command into inner (execution) and outer (interactive) variants when:
1. The command has both interactive selection and programmatic invocation paths
2. Python can perform optimizations (state updates, validation) before launching Claude
3. Parallel session coordination requires early state reservation

## Architecture

**Outer command**: Handles interactive selection when inputs are unknown. User-facing.
**Inner command**: Handles execution when all inputs are known. Called programmatically.

The CLI determines which command to launch based on whether inputs are fully known:
- Unknown inputs: Launch outer command, let Claude handle selection
- Known inputs: Update state in Python, launch inner command

## Example: objective-plan Split

See `src/erk/cli/commands/objective/plan_cmd.py` for the implementation.

Key elements:
- `_handle_interactive()` routes between inner/outer based on `--node` presence
- Inner command at `.claude/commands/erk/system/objective-plan-node.md`
- Outer command at `.claude/commands/erk/objective-plan.md`

## Benefits

1. **Reduced race windows**: State updates happen before `os.execvp()` replaces the process
2. **Skipped redundant steps**: Inner command bypasses interactive selection steps
3. **Clear separation**: Python handles state mutation, Claude handles planning/implementation

## Related Patterns

- Agent delegation patterns: See `docs/learned/planning/agent-delegation.md`
- Two-phase validation: Different pattern for validation before execution
```

---

#### 2. Pre-Marking Pattern for Objective Nodes

**Location:** `docs/learned/objectives/pre-marking-pattern.md`
**Action:** CREATE
**Source:** [Plan], [Impl], [PR #8176]

**Draft Content:**

```markdown
---
read-when:
  - implementing parallel session coordination for objectives
  - updating roadmap node status before plan creation
  - working on objective-plan workflow
tripwires: 1
---

# Pre-Marking Pattern for Objective Nodes

## Problem

When multiple parallel sessions run `/erk:objective-plan`, they may select the same eligible node before any marks it as "planning". This wastes effort and creates merge conflicts.

## Solution

Mark nodes as "planning" before Claude starts. When the CLI knows the target node (via `--next` or `--node`), pre-mark in Python before launching the agent.

## Implementation

The pre-marking helper uses a best-effort pattern:

See `src/erk/cli/commands/objective/plan_cmd.py`, function `_mark_node_planning`.

Key characteristics:
- Status-only update (no PR number required)
- Uses `_replace_node_refs_in_body` with `explicit_status="planning"`
- Silent error handling (agent retries if needed)

## Workflow Integration

1. CLI resolves target node (from `--next` or explicit `--node`)
2. CLI calls `_mark_node_planning()` (best-effort, silent failures)
3. CLI launches inner command with known node
4. Agent proceeds with planning (node already marked)

## Failure Modes

- **Pre-marking fails**: Agent marks node when it reaches that step (existing behavior)
- **Parallel race**: Window reduced but not eliminated; first to mark wins
- **Node already marked**: Update is idempotent, no harm done

## Related Documentation

- Roadmap status system: See `docs/learned/objectives/roadmap-status-system.md`
- Objective lifecycle: See `docs/learned/objectives/objective-lifecycle.md`
```

---

#### 3. `/erk:system:objective-plan-node` Command Reference

**Location:** `docs/learned/commands/objective-plan-split-pattern.md`
**Action:** CREATE
**Source:** [PR #8176]

**Draft Content:**

```markdown
---
read-when:
  - working on objective-plan command
  - understanding inner/outer command architecture in practice
  - debugging objective-plan routing issues
---

# Objective-Plan Inner/Outer Split

## Architecture Overview

The `/erk:objective-plan` command is split into two variants:

| Variant | Path | Invoked When |
|---------|------|--------------|
| Outer | `/erk:objective-plan` | User runs `erk objective plan` without known node |
| Inner | `/erk:system:objective-plan-node` | CLI knows target node (via `--next` or `--node`) |

## Inner Command: `/erk:system:objective-plan-node`

See `.claude/commands/erk/system/objective-plan-node.md` for the full command.

**Signature:** `<issue-number> --node <node-id>`

**Responsibilities:**
- Create objective-context marker
- Gather context (issue body, comments, linked plans)
- Enter plan mode for the specified node

**What it skips:** Interactive node selection (Steps 1-4 of outer command)

## Routing Logic

See `src/erk/cli/commands/objective/plan_cmd.py`, function `_handle_interactive`.

Decision tree:
1. Is `--node` explicitly provided? -> Inner command
2. Is `--next` flag set? -> Resolve to node, then inner command
3. Neither? -> Outer command (interactive selection in Claude)

## Pre-Marking Integration

When routing to inner command, CLI pre-marks the node as "planning" before launch.
See `docs/learned/objectives/pre-marking-pattern.md` for details.

## Related

- General pattern: See `docs/learned/commands/inner-outer-command-pattern.md`
- Pre-marking: See `docs/learned/objectives/pre-marking-pattern.md`
```

---

### MEDIUM Priority

#### 1. Best-Effort Helper Pattern

**Location:** `docs/learned/architecture/best-effort-updates.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - creating helpers that update external state before agent launch
  - deciding error handling strategy for pre-flight operations
---

# Best-Effort Helper Pattern

## When to Use

Use best-effort (silent error handling) for state updates when:
1. The operation is an optimization, not a requirement
2. An agent will retry the operation if it failed
3. Failure should not block the user from proceeding

## Pattern

Best-effort helpers catch all exceptions and fail silently:

See `src/erk/cli/commands/objective/plan_cmd.py`, function `_mark_node_planning` for an example.

Key characteristics:
- Broad exception handling
- No error propagation
- Idempotent operations preferred

## When NOT to Use

- Operation is required for correctness
- No retry mechanism exists
- Failure needs user notification

## Example: Pre-Marking

The `_mark_node_planning` helper is best-effort because:
- The inner command will mark the node if pre-marking failed
- Marking is an optimization to reduce race windows
- User can still plan even if pre-marking fails
```

---

#### 2. Test Fixture Selection Pattern

**Location:** `docs/learned/testing/test-context-upgrade.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - tests fail with NoRepoSentinel errors
  - command code needs ctx.repo.root or ctx.issues
  - migrating tests from context_for_test to erk_isolated_fs_env
tripwires: 1
---

# Test Fixture Selection: context_for_test vs erk_isolated_fs_env

## Fixture Comparison

| Fixture | Provides | Use When |
|---------|----------|----------|
| `context_for_test` | Lightweight context with defaults | Command doesn't access repo or GitHub |
| `erk_isolated_fs_env` | Full repo environment + GitHub fakes | Command needs `ctx.repo.root`, `ctx.issues`, or GitHub API |

## Migration Trigger

Upgrade to `erk_isolated_fs_env` when:
- Command code accesses `ctx.repo.root`
- Command code calls `ctx.issues.*` methods
- Test needs to verify GitHub API side effects

## Migration Steps

1. Replace `context_for_test` fixture with `erk_isolated_fs_env`
2. Create required fixtures (e.g., objective issues via `create_obj_issue`)
3. Access fakes via `ctx.issues` for verification
4. Update assertions to check fake gateway state

## Common Error

```
AttributeError: 'NoRepoSentinel' object has no attribute 'root'
```

This error indicates the command needs repo context but test uses `context_for_test`.
Solution: Migrate to `erk_isolated_fs_env`.

## Example Migration

See `tests/commands/objective/test_plan.py`, function `test_plan_with_node_flag` for a migrated test.
```

---

#### 3. Pre-Marking Test Verification Pattern

**Location:** `docs/learned/testing/api-side-effect-verification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - testing commands that make GitHub API calls
  - verifying pre-marking or state updates happened
  - inspecting fake gateway state after command execution
---

# API Side Effect Verification Pattern

## Purpose

Verify that commands make expected GitHub API calls by inspecting fake gateway state after execution.

## Pattern

1. Run command with fake gateway
2. Access fake state (e.g., `fake_issues.updated_bodies`)
3. Assert expected API calls occurred

## Example: Verifying Pre-Marking

See `tests/commands/objective/test_plan.py` for examples of this pattern.

Key verification points:
- Check `fake_issues.updated_bodies` contains the issue number
- Parse the updated body to verify new status
- Confirm the update happened before agent launch (by checking call order)

## Common Fake State Accessors

| Fake | State Property | What It Tracks |
|------|---------------|----------------|
| `FakeGitHubIssues` | `updated_bodies` | Issue body updates |
| `FakeGitHubIssues` | `created_issues` | Newly created issues |
| `FakeGitHubPRs` | `created_prs` | Newly created PRs |
```

---

#### 4. Command Variant Test Coverage

**Location:** `docs/learned/testing/command-variant-coverage.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - testing commands with inner/outer variants
  - ensuring complete coverage for command splits
---

# Command Variant Test Coverage Checklist

## When a Command Has Inner/Outer Variants

Test all paths:

1. **Outer command path**
   - No explicit inputs (interactive selection)
   - Verify outer command string constructed
   - Verify NO pre-flight state updates

2. **Inner command path (explicit input)**
   - Explicit `--node` or equivalent flag
   - Verify inner command string constructed
   - Verify pre-flight state updates occurred

3. **Inner command path (resolved input)**
   - Resolved via `--next` or equivalent
   - Verify resolution logic
   - Verify inner command string constructed
   - Verify pre-flight state updates occurred

4. **Helper function**
   - Unit test the state update helper directly
   - Test success case
   - Test failure handling (best-effort should not raise)

## Example

See `tests/commands/objective/test_plan.py` for complete coverage of objective-plan variants.
```

---

#### 5. Command File Organization

**Location:** `docs/learned/commands/command-file-organization.md`
**Action:** CREATE
**Source:** [PR #8176]

**Draft Content:**

```markdown
---
read-when:
  - creating new slash commands
  - deciding where to place command files
  - understanding system/ subdirectory purpose
---

# Command File Organization

## Directory Structure

```
.claude/commands/erk/
├── command-name.md          # User-facing commands
└── system/
    └── internal-command.md  # Internal/programmatic commands
```

## Placement Criteria

| Criterion | Top-level | system/ |
|-----------|-----------|---------|
| User invokes directly | Yes | No |
| Called by other commands | Either | Preferred |
| Implementation detail | No | Yes |
| Appears in help/discovery | Yes | No |

## Example

- `/erk:objective-plan` - User-facing, top-level
- `/erk:system:objective-plan-node` - Internal, called by CLI, in system/

## Naming Convention

System commands use the `system:` namespace prefix to indicate they are internal implementation details.
```

---

### LOW Priority

#### 1. Update `/erk:objective-plan` Command Doc

**Location:** `.claude/commands/erk/objective-plan.md`
**Action:** UPDATE
**Source:** [PR #8176]

**Draft Content:**

Add reference to split-pattern documentation in the command file. Do NOT duplicate the split explanation, just add a pointer:

```markdown
<!-- Add near the top of the file, after the description -->

## Implementation Notes

This command uses an inner/outer split for parallel session coordination.
See `docs/learned/commands/objective-plan-split-pattern.md` for architecture details.
```

---

## Contradiction Resolutions

**None found.** No contradictions detected between existing documentation and the plan implementation.

All existing docs are harmonious with the new patterns:
- Pre-marking aligns with existing "planning" status documentation in `docs/learned/objectives/roadmap-status-system.md`
- Inner/outer split preserves existing objective-plan workflow
- Delegation patterns already established in `docs/learned/planning/agent-delegation.md`
- Marker patterns already used for objective-context and roadmap-step

---

## Stale Documentation Cleanup

**None found.** All referenced code artifacts were verified to exist. No phantom references detected in existing documentation.

---

## Prevention Insights

Both sessions (planning + implementation parts 1-2) completed without errors or failed approaches, indicating strong planning quality and effective use of existing documentation. The prevention insights below are forward-looking patterns discovered during implementation:

### 1. Race Condition in Parallel Sessions

**What happened:** Objective nodes could be marked "planning" only after Steps 1-5 in Claude, leaving a wide window for parallel sessions to select the same node.

**Root cause:** Marking happened too late in the flow, after interactive selection.

**Prevention:** When the CLI knows the target node, pre-mark in Python before launching Claude. This reduces the race window to near-zero.

**Recommendation:** TRIPWIRE - Added to planning and commands tripwires.

### 2. Test Fixture Mismatch

**What happened:** Tests using `context_for_test` fail when command code accesses `ctx.repo.root` because the lightweight fixture defaults repo to `NoRepoSentinel`.

**Root cause:** Fixture selection doesn't match command requirements.

**Prevention:** When command paths call helpers needing repo context, use `erk_isolated_fs_env` instead of `context_for_test`.

**Recommendation:** TRIPWIRE - Added to testing tripwires.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Pre-marking for known nodes

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before splitting commands into inner/outer or when adding parallel session coordination
**Warning:** "CRITICAL: If the command coordinates parallel sessions, the CLI must pre-mark state before launching the inner command to prevent race conditions. See docs/learned/objectives/pre-marking-pattern.md"
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents agents from implementing inner/outer splits without considering race conditions. The destructive potential is high because parallel sessions selecting the same node wastes significant agent compute and creates merge conflicts.

### 2. Test fixture selection (context_for_test vs erk_isolated_fs_env)

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When `_handle_interactive` or command paths call helpers that need ctx.repo.root or ctx.issues
**Warning:** "CRITICAL: Tests must use erk_isolated_fs_env, not context_for_test. The lightweight fixture defaults repo to NoRepoSentinel(). See docs/learned/testing/test-context-upgrade.md"
**Target doc:** `docs/learned/testing/tripwires.md`

The error message about NoRepoSentinel doesn't immediately suggest fixture upgrade, making this non-obvious. Tests may even pass with `context_for_test` if the test path doesn't exercise repo access, leading to false confidence.

### 3. Status-only roadmap updates

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When updating roadmap nodes without a PR number
**Warning:** "PATTERN: Use _replace_node_refs_in_body(new_pr=None, explicit_status='...') for status-only updates without PR numbers. See docs/learned/objectives/pre-marking-pattern.md"
**Target doc:** `docs/learned/objectives/tripwires.md`

This pattern is not obvious from reading the code, and any code updating roadmap node status may need this approach. The function signature suggests PR is required, but passing None with explicit_status enables status-only updates.

---

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. Best-effort helper pattern

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Silent error handling is justified by agent retry, but may confuse developers who expect errors to propagate. Could be promoted if more best-effort helpers are added to the codebase.

### 2. Pre-marking verification in tests

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** Testing API side effects via fake gateway inspection is a general pattern. Specific to pre-marking use case in this PR, but the pattern itself is already established. May warrant a more general API side-effect testing doc.

---

## Tripwire Additions Summary

The following tripwires should be added to existing tripwire files:

**docs/learned/planning/tripwires.md** (2 new):
1. Pre-marking for parallel session coordination
2. State update timing optimization (Python before launch)

**docs/learned/commands/tripwires.md** (2 new):
1. Inner/outer command split consideration
2. Programmatic argument optimization

**docs/learned/testing/tripwires.md** (1 new):
1. Test fixture selection for repo context

**docs/learned/objectives/tripwires.md** (1 new):
1. Status-only roadmap updates pattern

---

## Documentation Structure

Recommended file organization based on the gap analysis:

```
docs/learned/
├── commands/
│   ├── inner-outer-command-pattern.md          # NEW (HIGH priority)
│   ├── objective-plan-split-pattern.md         # NEW (HIGH priority)
│   ├── command-file-organization.md            # NEW (MEDIUM priority)
│   └── tripwires.md                            # UPDATE (add 2 tripwires)
│
├── objectives/
│   ├── pre-marking-pattern.md                  # NEW (HIGH priority)
│   └── tripwires.md                            # UPDATE (add 1 tripwire)
│
├── architecture/
│   └── best-effort-updates.md                  # NEW (MEDIUM priority)
│
├── testing/
│   ├── test-context-upgrade.md                 # NEW (MEDIUM priority)
│   ├── api-side-effect-verification.md         # NEW (MEDIUM priority)
│   ├── command-variant-coverage.md             # NEW (MEDIUM priority)
│   └── tripwires.md                            # UPDATE (add 1 tripwire)
│
└── planning/
    └── tripwires.md                            # UPDATE (add 2 tripwires)

.claude/commands/erk/
└── objective-plan.md                           # UPDATE (add reference)
```

**Total new documentation files:** 9
**Total updated files:** 6 (1 command doc + 5 tripwire files)

---

## Cross-Reference Requirements

After creating documentation, ensure these cross-references are in place:

1. `inner-outer-command-pattern.md` <-> `objective-plan-split-pattern.md` (bidirectional)
2. `pre-marking-pattern.md` <-> `objective-plan-split-pattern.md` (bidirectional)
3. `test-context-upgrade.md` <-> `command-variant-coverage.md` (related patterns)
4. `inner-outer-command-pattern.md` -> `docs/learned/planning/agent-delegation.md` (contrast)
5. `pre-marking-pattern.md` -> `docs/learned/objectives/roadmap-status-system.md` (extends)
6. `pre-marking-pattern.md` -> `docs/learned/objectives/objective-lifecycle.md` (context)
