---
title: Phase 0 Detection Pattern
read_when:
  - implementing mode variants in multi-phase commands
  - designing conditional execution workflows
  - debugging scattered mode detection logic
tripwires:
  - action: "detecting mode after Phase 0 has already executed"
    warning: "Late detection wastes work and creates scattered conditionals across all phases"
    score: 5
last_audited: "2026-02-16 14:10 PT"
audit_result: clean
---

# Phase 0 Detection Pattern

## Why Phase 0 Exists

Multi-phase commands often support fundamentally different operational modes (code review vs plan file editing, interactive vs batch, local vs remote). **The timing of mode detection determines code clarity**: detect early and branch cleanly, or detect late and scatter `if mode == X` checks across every phase.

Phase 0 detection solves this by **deciding the execution path before any work begins**, preventing wasted effort and keeping mode-specific logic consolidated.

## The Core Problem

Without upfront detection, commands suffer from:

1. **Starting in the wrong mode** — begin Phase 1 work, discover incorrect mode in Phase 2, backtrack
2. **Scattered conditionals** — every phase checks `if mode == X`, duplicating logic
3. **Unclear execution flow** — difficult to understand which code runs in which mode
4. **Wasted computation** — execute phases irrelevant to the current mode

The symptom: "Wait, this is plan file mode? But I already classified the feedback as code comments..."

## The Solution: Detect Before Execute

Add **Phase 0** as the first step:

1. **Detect mode** based on context (labels, flags, files, environment)
2. **Branch the entire flow** — mode-specific paths become separate sections
3. **Skip irrelevant phases** — only run phases that apply to the detected mode

This creates a decision tree at the entry point rather than conditionals scattered throughout.

## Pattern in Practice: pr-address

<!-- Source: .claude/commands/erk/pr-address.md, Phase 0 section -->

The `/erk:pr-address` command uses Phase 0 detection to determine which workflow to follow:

1. **File-based detection** — checks if `.erk/impl-context/plan.md` is git-tracked → Plan File Mode
2. **Default** → Code Review Mode (Phases 1-6)

### File-Based: Plan File Mode

Plan-only PRs (created by the plan save workflow) have `.erk/impl-context/plan.md` committed to the branch. Detection uses `git ls-files --error-unmatch`.

### Why This Works

**Single decision point**: Mode logic lives in Phase 0. Later phases don't check the mode — they simply don't run if an alternative mode is active.

**Complete separation**: The command document has distinct sections for each mode. Anyone reading the command knows exactly which phases run in which mode without tracking conditionals.

**No mode leakage**: Each mode's phases never see another mode's context or logic.

## Detection Mechanisms

### Label-Based Detection

Check for a PR label to determine mode:

```bash
gh pr view --json labels -q '.labels[].name'
```

If the label exists in the output, switch to alternative mode.

**Why labels work**: Labels are applied by automated workflows and remain stable throughout the PR lifecycle. They're a durable signal of PR intent.

### Flag-Based Detection

Command-line flags provide explicit mode selection:

```bash
my-command --dry-run
```

The flag determines whether to execute mutations or just simulate them.

**Trade-off**: Flags require user knowledge. Labels are set by workflows and don't require user decision.

### Environment-Based Detection

Check environment variables:

```bash
if [ "$CI" = "true" ]; then
  # CI mode
else
  # Local mode
fi
```

**Why this works**: CI environment is a stable signal. Local vs CI often have different constraints (no interactivity in CI, different permissions).

### File-Based Detection

Check for presence/absence of files:

```bash
if [ -f ".erk/impl-context/plan.md" ]; then
  # Plan implementation mode
else
  # Ad-hoc development mode
fi
```

**Trade-off**: File-based detection assumes files are stable indicators. If files can be stale or partially written, this becomes unreliable.

## When to Use Phase 0

Use Phase 0 detection when:

- **Multi-phase command**: The command has sequential phases (Phase 1, 2, 3...)
- **Mode changes fundamental behavior**: Not just a flag tweaking one step, but a different execution path
- **Multiple phases affected**: If only one phase cares about the mode, add a conditional there instead
- **Modes are mutually exclusive**: Can't be in both modes simultaneously

## When NOT to Use Phase 0

Skip Phase 0 when:

- **Single-phase command**: No phases to orchestrate, just add `if` to the one place that cares
- **Mode is additive**: Both paths execute, mode just adds extra behavior on top
- **Mode affects one phase only**: Add conditional in that phase rather than creating upfront detection
- **Modes can overlap**: Not binary — multiple modes can be active, so detection isn't clean branching

## Anti-Patterns

### WRONG: Late Detection

```markdown
### Phase 1: Classify Feedback

1. Fetch feedback
2. Parse comments
3. Check if plan file mode
4. ERROR: Should have checked this before Phase 1 started
```

**Why wrong**: Already fetched and parsed feedback assuming code review mode. Wasted work.

**Correct approach**: Phase 0 detects mode, Phase 1 only runs if code review mode is active.

### WRONG: Scattered Detection

```markdown
### Phase 1: Classify

- If plan file: classify differently

### Phase 2: Generate

- If plan file: generate differently

### Phase 3: Apply

- If plan file: apply differently
```

**Why wrong**: Mode logic duplicated across every phase. Hard to understand the two execution paths.

**Correct approach**: Phase 0 branches to separate flows. Each flow has its own Phase 1/2/3 without conditionals.

### WRONG: No Detection Until Failure

```markdown
### Phase 2: Generate Fixes

1. Try to generate code fixes
2. Realize the PR is a plan-only PR
3. Abort with error
```

**Why wrong**: Phase 2 is too late to discover mode. Should have detected in Phase 0 and never entered Phase 1.

**Correct approach**: Phase 0 detects plan file and branches to plan file flow immediately.

## Related Patterns

### State Machine Entry Point

Phase 0 detection is a state machine entry point:

- **State**: The detected mode (code review, plan file)
- **Transitions**: Moving through phases within that mode
- **Guards**: The detection logic determines initial state

Once the initial state is determined, transitions within that mode never cross to the other mode's transitions.

## Implementation Checklist

When adding Phase 0 detection to a command:

- [ ] Create Phase 0 section at the top of the command document
- [ ] Identify detection mechanism (label, flag, file, environment)
- [ ] Document both modes clearly (what makes them different, not just "mode A vs mode B")
- [ ] Branch entire execution flow (normal phases vs alternative mode section)
- [ ] Test both paths (ensure both modes work correctly from Phase 0 onward)
- [ ] Update command description (explain when each mode activates)

## Related Documentation

- [Workflow Gating Patterns](../ci/workflow-gating-patterns.md) — Conditional execution in CI contexts
- [PR Address Workflows](../erk/pr-address-workflows.md) — Complete pr-address workflow including both modes
