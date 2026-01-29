---
title: Phase 0 Detection Pattern
read_when:
  - adding conditional execution to phase-based commands
  - implementing mode variants in CLI commands
  - modifying pr-address or similar multi-phase workflows
tripwires:
  - action: "Detect mode in Phase 0 before any other phases execute"
    warning: "Late detection leads to starting wrong mode then discovering the error"
    score: 5
---

# Phase 0 Detection Pattern

A pattern for commands that have multiple operational modes. When a command can operate in fundamentally different ways, detect the mode in **Phase 0** before any other phases execute.

## The Problem

Commands often have mode variants that change fundamental behavior:

- **Code review** vs **plan review** (different file types, different sync mechanisms)
- **Interactive** vs **batch** (different user interaction patterns)
- **Local** vs **remote** (different data sources)

If mode detection happens late or is scattered across phases, you get:

1. **Started in wrong mode**: Begin Phase 1 work, then discover wrong mode in Phase 2
2. **Scattered conditionals**: Every phase has `if mode == X` checks
3. **Complex logic**: Difficult to understand which code runs in which mode
4. **Wasted work**: Execute phases that don't apply to the current mode

## The Solution: Phase 0 Detection

Add a **Phase 0** at the start that:

1. **Detects the mode** based on context (labels, flags, environment)
2. **Branches the entire execution flow** into mode-specific paths
3. **Ensures no other phases run** until mode is determined

This creates a clean separation: detect once, then follow the appropriate path.

## Example: pr-address Command

The `/erk:pr-address` command has two modes:

- **Code review mode**: Address code review feedback on a code PR
- **Plan review mode**: Address plan review feedback on a plan-only PR

### Phase 0 Implementation

```markdown
### Phase 0: Plan Review Detection

Before classifying feedback, determine if this is a plan review PR:

1. Get the current PR number: `gh pr view --json number -q .number`
2. Check if the PR has the `plan-review` label: `gh pr view --json labels -q '.labels[].name'` and check for `plan-review` in the output
3. If YES: extract the plan issue number from the PR body (which contains `**Plan Issue:** #NNN`): `gh pr view --json body -q .body` and parse the issue number from the `**Plan Issue:** #NNN` line. Enter **Plan Review Mode** (see [Plan Review Mode](#plan-review-mode) below). Skip normal Phases 1-4.
4. If NO: proceed with standard code review flow (Phase 1)
```

**Source:** `.claude/commands/erk/pr-address.md:30-37`

### Why This Works

**Single detection point**: All mode logic is in Phase 0. Phases 1-4 don't need to check the mode.

**Complete branching**: If plan review mode is detected, the entire execution flow switches. Normal phases are skipped.

**Clear separation**: The command document has separate sections for each mode:

- Phase 0: Detection
- Phases 1-4: Code review mode
- Separate section: Plan review mode

Anyone reading the command knows exactly which phases run in which mode.

## Detection Mechanisms

### Label-Based Detection

Check for a label on the PR:

```bash
gh pr view --json labels -q '.labels[].name'
```

If the label exists, switch to the alternative mode.

**Example:** `plan-review` label indicates plan review mode.

**Source:** `src/erk/cli/constants.py:52` defines `PLAN_REVIEW_LABEL = "plan-review"`

### Flag-Based Detection

Check for command-line flags:

```python
@click.option("--dry-run", is_flag=True)
def my_command(dry_run: bool) -> None:
    if dry_run:
        # Dry-run mode
        ...
    else:
        # Normal mode
        ...
```

### Environment-Based Detection

Check environment state:

```python
if os.getenv("CI") == "true":
    # CI mode
    ...
else:
    # Local mode
    ...
```

### File-Based Detection

Check for the presence or absence of files:

```python
if Path(".impl/plan.md").exists():
    # Plan implementation mode
    ...
else:
    # Ad-hoc development mode
    ...
```

## When to Use This Pattern

Use Phase 0 detection when:

- **Command has phase-based execution**: Multiple sequential phases
- **Mode variant changes fundamental behavior**: Not just a flag that tweaks one step
- **Mode affects multiple phases**: If only one phase cares, just add a conditional there
- **Mode is mutually exclusive**: Can't be in both modes at once

## When NOT to Use This Pattern

Skip Phase 0 detection when:

- **Single-phase command**: No phases to orchestrate
- **Mode is optional**: Both paths execute, mode just adds extra behavior
- **Mode only affects one phase**: Add conditional in that phase instead
- **Mode is not binary**: More than two modes, or modes can overlap

## Anti-Patterns

### Anti-Pattern: Late Detection

**BAD:**

```markdown
### Phase 1: Classify Feedback

1. Fetch feedback
2. Check if plan review mode
3. If plan review: stop, you should have done this before Phase 1
```

**GOOD:**

```markdown
### Phase 0: Detect Mode

1. Check if plan review mode
2. If yes: enter plan review flow
3. If no: continue to Phase 1
```

### Anti-Pattern: Scattered Detection

**BAD:**

```markdown
### Phase 1: Classify Feedback

- If plan review mode: classify differently

### Phase 2: Generate Fixes

- If plan review mode: generate differently

### Phase 3: Apply Changes

- If plan review mode: apply differently
```

**GOOD:**

```markdown
### Phase 0: Detect Mode

1. Detect mode once
2. Branch to appropriate flow

### Code Review Mode

- Phase 1: Classify
- Phase 2: Generate
- Phase 3: Apply

### Plan Review Mode

- Phase 1: Edit plan
- Phase 2: Sync to GitHub
- Phase 3: Resolve threads
```

### Anti-Pattern: No Detection

**BAD:**

```markdown
### Phase 1: Classify Feedback

1. Try to classify code feedback
2. If that fails, maybe it's a plan review?
3. Error: confused state
```

**GOOD:**

```markdown
### Phase 0: Detect Mode

1. Explicitly check what mode we're in
2. Branch early, fail fast if unknown
```

## Related Patterns

### Label-Driven Branching

Phase 0 detection often uses labels as feature switches:

- Labels represent mode variants
- Detection checks for specific labels
- Labels are applied automatically by workflows

**Example:** `plan-review` label is applied by `erk exec plan-create-review-pr`, then detected by Phase 0 in `/erk:pr-address`.

### State Machine Transitions

Phase 0 detection can be seen as a state machine entry point:

- **State**: The mode detected (code review, plan review)
- **Transitions**: Moving through phases within that mode
- **Guards**: The detection logic that determines the initial state

## Implementation Checklist

When adding Phase 0 detection:

- [ ] Create Phase 0 section in command document
- [ ] Identify detection mechanism (label, flag, file, environment)
- [ ] Document both modes clearly (what makes them different)
- [ ] Branch entire execution flow (skip normal phases for alternative mode)
- [ ] Test both paths (ensure both modes work correctly)
- [ ] Update command description (explain when each mode is used)

## Related Documentation

- [Workflow Gating Patterns](../ci/workflow-gating-patterns.md) - Similar conditional execution in CI
- [PR Address Workflows](../erk/pr-address-workflows.md) - Complete pr-address workflow including both modes
- [Plan Review Workflow](../planning/pr-review-workflow.md) - The plan review mode triggered by Phase 0

## Attribution

Pattern implemented in PR address plan review mode (PR #6237 implementation).
