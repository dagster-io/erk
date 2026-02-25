# Documentation Plan: Mark objective nodes as planning in interactive flow

## Context

This PR (#8161) implements infrastructure for preventing parallel planning sessions from selecting the same objective roadmap node. When multiple Claude sessions work on the same objective, they could previously both select the same pending node, causing duplicate work. The solution marks selected nodes as "planning" status before launching Claude, so subsequent sessions automatically skip to the next available node.

The implementation required changes across multiple layers: visual distinction (new sparkline symbol), selection logic (fallback chain), CLI capability (status-only updates), and workflow integration (convergence point pattern). A significant mid-session correction from the user redirected the implementation from CLI-based marking to convergence-point marking, demonstrating the importance of tracing all user-facing paths to find where they converge before implementing shared behavior.

Key insights for future agents include: (1) the os.execvp timing constraint where state must persist before process replacement, (2) the convergence point pattern for implementing shared behavior across multiple entry points, and (3) the inner/outer skill split pattern for commands with both interactive and programmatic paths.

## Raw Materials

PR #8161: Mark objective nodes as planning in interactive flow

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 4 |

## Stale Documentation Cleanup

**No stale documentation found.** All existing docs verified as referencing current code artifacts.

## Documentation Items

### HIGH Priority

#### 1. os.execvp timing constraint

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 551fdae2

**Draft Content:**

```markdown
### Before calling launch_interactive() or os.execvp()

**Context:** `launch_interactive()` uses `os.execvp()` which replaces the current process.

**Rule:** Any state updates that must persist (file writes, GitHub API calls, database changes) MUST happen BEFORE the launch call.

**Why:** `os.execvp()` replaces the current process - nothing after the call will execute.

**Example:**
- CORRECT: Mark node status, THEN call `launch_interactive()`
- WRONG: Call `launch_interactive()`, THEN mark node status (NEVER EXECUTES)

See `src/erk/cli/commands/objective/plan_cmd.py` for implementation patterns using `launch_interactive()`.

**grep:** `os.execvp`, `launch_interactive`
```

---

#### 2. Planning symbol distinction

**Location:** `docs/learned/objectives/roadmap-status-system.md`
**Action:** UPDATE
**Source:** [PR #8161] Diff analysis

**Draft Content:**

```markdown
## Visual Symbol Updates

**Visual distinction:** Planning nodes render with a distinct symbol `◐` (half-circle) in sparklines, visually different from in-progress nodes `▶` (triangle). This helps users identify which nodes are in autonomous planning vs active implementation.

**Current symbol mapping:**
- `✓` done
- `▶` in_progress
- `◐` planning (distinct from in_progress)
- `○` pending
- `⊘` blocked
- `-` skipped

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` for symbol definitions.

**grep:** `_STATUS_SYMBOLS` or `"planning": "◐"`
```

---

#### 3. Parallel planning prevention

**Location:** `docs/learned/planning/parallel-planning-prevention.md`
**Action:** CREATE
**Source:** [Plan] + [Impl] All sessions

**Draft Content:**

```markdown
# Parallel Planning Prevention

## Problem

When multiple Claude sessions work on the same objective, both sessions could select the same pending node, causing work collision and duplicate effort.

## Solution

The interactive planning workflow marks selected nodes as "planning" status before launching Claude:

1. User invokes `erk objective plan <issue>` (with or without `--next`/`--node`)
2. CLI or interactive selection resolves which node to plan
3. **BEFORE launching Claude:** Mark node as planning via `erk exec update-objective-node`
4. Launch Claude with the planning context
5. Subsequent sessions skip planning nodes via fallback chain: pending -> planning -> in_progress

## Visual Indicators

Planning nodes render with distinct symbol `◐` in sparklines:
```
○○◐▶✓  (2 pending, 1 planning, 1 in_progress, 1 done)
```

## Workflow Integration

The marking happens at the convergence point (`.claude/commands/erk/objective-plan.md`) where all user-facing paths meet.

See the convergence point pattern doc for why this architecture was chosen.

**Source files:**
- Workflow: `.claude/commands/erk/objective-plan.md`
- CLI: `src/erk/cli/commands/objective/plan_cmd.py`
- Symbol: `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

**grep:** `update-objective-node`, `--status planning`, `◐`
```

---

### MEDIUM Priority

#### 4. Extended fallback chain

**Location:** `docs/learned/objectives/dependency-graph.md`
**Action:** UPDATE
**Source:** [PR #8161] Diff analysis

**Draft Content:**

```markdown
## Three-Tier Fallback Chain

`find_graph_next_node()` applies a three-tier fallback when selecting the next actionable node:

1. **pending (unblocked)** - First look for unblocked pending nodes via `graph.next_node()`
2. **planning (unblocked)** - If no pending, fall back to first unblocked planning node
3. **in_progress** - If no planning, fall back to first in_progress node from phase list

This ensures the TUI always shows an actionable next step, even when all pending nodes are in planning status.

**Example:**
```
Nodes: ○○◐◐▶
Fallback chain: No pending available -> Select first ◐ (planning)
```

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` for fallback implementation.

**grep:** `find_graph_next_node`
```

---

#### 5. Status-only updates CLI capability

**Location:** `docs/learned/cli/status-only-updates.md`
**Action:** CREATE
**Source:** [Impl] Session 5eb68e86

**Draft Content:**

```markdown
# Status-Only Updates Pattern

## Pattern

CLI commands with optional mutually-exclusive parameters require validation that at least one is provided.

## Example: update-objective-node

**Behavior:**
- `--pr` is optional (default: preserve existing)
- `--status` is optional (default: preserve existing)
- **Validation:** At least one must be provided

**Usage:**
```bash
# Update both PR and status
erk exec update-objective-node 42 --node abc --pr 123 --status in_progress

# Status-only update (preserve existing PR)
erk exec update-objective-node 42 --node abc --status planning

# ERROR: Must provide at least one
erk exec update-objective-node 42 --node abc
```

## Implementation Pattern

When making CLI options optional, add validation requiring at least one:
```python
if pr is None and status is None:
    raise ValueError("Must provide at least one of --pr or --status")
```

See `src/erk/cli/commands/exec/scripts/update_objective_node.py` for implementation.

**grep:** `update_objective_node`, `--pr`, `--status`
```

---

#### 6. Convergence point pattern

**Location:** `docs/learned/planning/convergence-point-pattern.md`
**Action:** CREATE
**Source:** [Impl] Session 5eb68e86 (major user correction)

**Draft Content:**

```markdown
# Convergence Point Pattern

## Pattern

When multiple user-facing entry points need the same behavior, implement it at the convergence point (where all paths meet) rather than duplicating logic across entry points.

## Anti-Pattern

Implementing shared logic at each entry point:
- CLI path 1: implements behavior
- CLI path 2: implements behavior (duplicated)
- Interactive path: forgets to implement behavior (bug!)

## Correct Pattern

Implement at convergence point where all paths meet. All entry points funnel to this single location, ensuring behavior cannot be forgotten.

## When to Apply

Use convergence point pattern when:
1. Multiple user-facing flows need identical behavior
2. The flows eventually meet at a single execution point
3. Missing the logic in one path would cause incorrect behavior

## Benefits

- **Single source of truth:** Logic defined once
- **Maintenance:** Updates apply to all paths automatically
- **Correctness:** Impossible to forget in one path

## Example from erk

**Problem:** Mark objective nodes as "planning" when user starts planning
**Entry points:** CLI with --next, CLI with --node, interactive selection
**Convergence:** `.claude/commands/erk/objective-plan.md` (all paths run this command)
**Solution:** Add marking step to command, not CLI

## Related

- **os.execvp constraint:** If convergence point is before process replacement, do work in Python before launch
- **Inner/outer skill pattern:** When CLI needs different behavior than convergence point, split into inner/outer

**Source:** Session 5eb68e86 major user correction, PR #8161 implementation

**grep:** `objective-plan.md`, `_handle_interactive`
```

---

#### 7. Inner/outer skill split pattern

**Location:** `docs/learned/commands/inner-outer-skill-pattern.md`
**Action:** CREATE
**Source:** [Plan] Session 551fdae2

**Draft Content:**

```markdown
# Inner/Outer Skill Pattern

## Pattern

When a command has both interactive (user selection) and programmatic (pre-resolved) paths, extract the post-selection logic into an inner skill that both paths can invoke.

## Structure

- **Outer skill:** Handles interactive selection when data is unknown
- **Inner skill:** Handles execution when data is known (markers, context, work)
- **CLI:** When data is known, does Python work then launches inner skill

## When to Apply

Use inner/outer split when:
1. Command has interactive selection step
2. Selection can be pre-resolved programmatically (CLI flags)
3. Post-selection logic is identical for both paths
4. CLI needs to do Python-only work before launching Claude

## Benefits

- **CLI optimization:** Python can do work before launching Claude
- **Code reuse:** Post-selection logic defined once (inner skill)
- **Clear separation:** Selection logic vs execution logic

## Flags

If a flag (like `--node`) is only passed programmatically:
- Users never invoke it directly
- CLI always resolves data before passing to inner skill
- Document as programmatic-only flag

**Source:** Session 551fdae2 pattern discovery

**grep:** `objective-plan.md`, `_handle_interactive`, `launch_interactive`
```

---

### LOW Priority

#### 8. Pre-existing test failure analysis

**Location:** `docs/learned/pr-operations/pre-existing-failure-analysis.md`
**Action:** CREATE
**Source:** [Impl] Session 64144371

**Draft Content:**

```markdown
# Pre-existing Test Failure Analysis

## Problem

When CI fails during PR review, default assumption is "my change broke the tests." This can waste time debugging unrelated failures.

## Analysis Pattern

Determine if test failures are pre-existing by analyzing code paths:

1. **Identify what you changed:** Which files, functions, code paths?
2. **Identify what tests failed:** Which test files, what code do they exercise?
3. **Trace the connection:** Do failing tests execute your changed code?

## When to Suspect Pre-existing

- Test failures in unrelated modules
- Failures in code paths your change doesn't touch
- Warnings vs actual test failures (check pytest summary)
- Failures present before your branch

## Verification

```bash
# Check if failures exist in base branch
git checkout main
pytest path/to/failing/test.py  # If fails, it's pre-existing
```

**Source:** Session 64144371 implementation

**grep:** test failure analysis patterns
```

---

#### 9. Devrun agent hallucination warnings

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 5eb68e86

**Draft Content:**

```markdown
### When devrun reports test failures but pytest shows passes

**Context:** Devrun agent can misinterpret warnings as test failures.

**Symptom:** Devrun claims "N test failures" but pytest summary shows "N passed, 0 failed"

**Verification:**
1. Check actual pytest summary line: "N passed" vs "N failed"
2. Look for ResourceWarnings or RuntimeWarnings that agent misread
3. Verify exit code (0 = success, 1 = failure)

**Prevention:** Always verify devrun agent claims by checking actual pytest output, not agent interpretation.

**grep:** devrun, test output
```

---

## Contradiction Resolutions

**No contradictions found.** All existing documentation is current and consistent with the new implementation.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Logic at wrong abstraction layer

**What happened:** Initially implemented node marking in `_handle_interactive` (CLI), which only covered CLI paths but not the interactive path where users select nodes inside Claude.
**Root cause:** Failed to trace all user-facing paths to find where they converge before implementing.
**Prevention:** Before implementing behavior that spans multiple user entry points, always trace to the convergence point first, then implement there.
**Recommendation:** TRIPWIRE - Convergence point pattern (score 4)

### 2. Test expectations for symbolic constants

**What happened:** Changed planning symbol from `▶` to `◐` but didn't update test expectations initially.
**Root cause:** Hardcoded test expectations for symbols.
**Prevention:** When changing constants like status symbols, grep for tests containing the old value: `Grep(pattern="▶", path="tests/")`.
**Recommendation:** ADD_TO_DOC - Testing conventions

### 3. NoRepoSentinel checks blocking tests

**What happened:** Added repo check at top of `_handle_interactive`, but tests use `context_for_test()` without real repo.
**Root cause:** Premature validation that made function untestable.
**Prevention:** Only add repo checks immediately before operations that require real repos; keep function testable with fakes.
**Recommendation:** CONTEXT_ONLY - Standard testing anti-pattern

### 4. Devrun agent hallucinated test failures

**What happened:** Devrun reported "9 test failures" but pytest showed "114 passed" with only warnings.
**Root cause:** Agent misinterpreted ResourceWarnings as failures.
**Prevention:** Always verify devrun agent claims by checking actual pytest summary line.
**Recommendation:** TRIPWIRE - Score 3, potential promotion

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. os.execvp timing constraint

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before calling `launch_interactive()` or any function using `os.execvp()`
**Warning:** Any state updates that must persist (file writes, GitHub API calls, database changes) MUST happen BEFORE the launch call - os.execvp() replaces the process so nothing after executes.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the behavior is fundamentally non-obvious (process replacement means code literally stops executing, not that it runs later), affects any command using `launch_interactive()`, and causes silent data loss when violated (state changes simply never happen, with no error).

### 2. Convergence point implementation

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern implied by user correction)
**Trigger:** Before implementing behavior that spans multiple user entry points
**Warning:** Trace all user-facing paths to find where they converge. Implement shared logic at the convergence point, not at each entry point - implementing at entry points risks forgetting one path.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the mid-session correction demonstrated significant wasted effort (entire `_mark_node_planning` function written and tested, then deleted). The pattern applies broadly to any feature spanning CLI and interactive paths.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Devrun agent hallucination

**Score:** 3/10 (criteria: Non-obvious +1, Repeated pattern +1, External tool quirk +1)
**Notes:** Only affects agent-driven development, not production code. May warrant promotion if more incidents accumulate showing agents misinterpreting pytest output.

### 2. Changing status symbols

**Score:** 2/10 (criteria: Repeated pattern +1, External tool quirk +1)
**Notes:** Moderate impact, requires test updates. Standard grep-before-change practice; may not need dedicated tripwire.

### 3. CLI options validation

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Standard pattern once learned, not cross-cutting. Already well-documented in Click best practices.

### 4. Logic at wrong abstraction layer

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** Overlaps with convergence point pattern (already scored as 4). Subsumed by that tripwire.
